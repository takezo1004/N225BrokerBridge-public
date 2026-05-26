using N225BrokerBridge.Application.Common;
using N225BrokerBridge.Domain.Brokers;
using N225BrokerBridge.Domain.Orders;
using N225BrokerBridge.Domain.Positions;
using N225BrokerBridge.Domain.ValueObjects;
using Microsoft.Extensions.Logging;

namespace N225BrokerBridge.Application.Orders;

/// <summary>
/// ブローカーから流れてくる <see cref="ExecutionEvent"/> を受け、
/// Order / Position 集約に反映するアプリケーションサービス。
///
/// 動作:
///   - 新規約定 (TradeType.NewOrder):
///       1. BrokerOrderId で Order を特定し ApplyExecution
///       2. 新規 Position を作成して保存
///   - 返済約定 (TradeType.ExitOrder):
///       1. BrokerOrderId で Order を特定し ApplyExecution
///       2. TargetPositionId で Position を特定し ApplyClosure
///       3. Position が IsClosed なら Repository から削除
///
/// 注意:
///   - 同じ ExecutionId が複数回届く想定はしない (broker 側が冪等性を保つ前提)
///   - Order/Position が見つからない場合は警告ログ + イベント破棄 (異常系)
///   - 本クラスは ExecutionEvent 単発処理に閉じる。ストリーム購読 (Rx.Subscribe) は
///     上位 (Hosted Service / UI) の責務。
/// </summary>
public sealed class ExecutionApplier
{
    private readonly IOrderRepository _orderRepo;
    private readonly IPositionRepository _positionRepo;
    private readonly Sync.IAutoPositionMetadataStore _autoStore;
    private readonly Sync.IPendingOrderTracker _pendingTracker;
    private readonly IDateTimeProvider _clock;
    private readonly ILogger<ExecutionApplier> _logger;

    public ExecutionApplier(
        IOrderRepository orderRepo,
        IPositionRepository positionRepo,
        Sync.IAutoPositionMetadataStore autoStore,
        Sync.IPendingOrderTracker pendingTracker,
        IDateTimeProvider clock,
        ILogger<ExecutionApplier> logger)
    {
        _orderRepo = orderRepo;
        _positionRepo = positionRepo;
        _autoStore = autoStore;
        _pendingTracker = pendingTracker;
        _clock = clock;
        _logger = logger;
    }

    public async Task ApplyAsync(ExecutionEvent execution, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(execution);

        var order = await _orderRepo.FindByBrokerOrderIdAsync(
            execution.BrokerCode, execution.BrokerOrderId, ct);

        if (order is null)
        {
            _logger.LogWarning(
                "ExecutionEvent for unknown order: broker={Broker} orderId={OrderId} execId={ExecId}",
                execution.BrokerCode, execution.BrokerOrderId, execution.ExecutionId);
            return;
        }

        // 1. Order に約定反映
        var fill = new Execution(execution.ExecutionId, execution.Quantity, execution.Price, execution.ExecutedAt);
        try
        {
            order.ApplyExecution(fill);
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogError(ex,
                "ApplyExecution failed: order={OrderId} execId={ExecId} qty={Qty}",
                order.Id, execution.ExecutionId, execution.Quantity);
            return;
        }
        await _orderRepo.UpdateAsync(order, ct);

        // Order が終端 (Filled / Cancelled / Expired / Rejected) なら pending 追跡から外す
        // 旧 N225OrderBridge の OrderInquiryList.Remove 相当
        if (order.IsTerminal && order.BrokerOrderId is not null)
        {
            _pendingTracker.Untrack(order.BrokerOrderId.Value);
        }

        // 2. 種別ごとに建玉処理
        switch (execution.TradeType)
        {
            case TradeType.NewOrder:
                await OpenPositionAsync(order, execution, ct);
                break;
            case TradeType.ExitOrder:
                await CloseTargetPositionAsync(execution, ct);
                break;
        }
    }

    /// <summary>
    /// ブローカー側で注文が終端状態 (取消/失効/拒否) になったことを反映する。
    /// 約定なしのキャンセル・失効では <see cref="ExecutionEvent"/> が発生しないため、
    /// 注文一覧ポーリングから呼び出して状態同期を取る。
    ///
    /// 動作:
    ///   - Order の残数量 (RemainingQuantity) を確認
    ///   - 0 なら全約定済みなので何もしない (通常の <see cref="ApplyAsync"/> 経路で処理済み)
    ///   - 1 以上なら Order を Cancelled でマーク + ExitOrder の場合は Position の予約を解放
    ///
    /// 冪等: 既に終端状態の Order に対しては何もしない。
    /// </summary>
    /// <param name="brokerCode">ブローカーコード。</param>
    /// <param name="brokerOrderId">終端遷移した注文のブローカー OrderId。</param>
    /// <param name="reason">終端理由 (ログ用)。</param>
    public async Task ApplyTerminationAsync(
        BrokerCode brokerCode,
        OrderId brokerOrderId,
        string? reason,
        CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(brokerCode);
        ArgumentNullException.ThrowIfNull(brokerOrderId);

        var order = await _orderRepo.FindByBrokerOrderIdAsync(brokerCode, brokerOrderId, ct);
        if (order is null) return;
        if (order.IsTerminal) return;   // 冪等

        var unfilled = order.RemainingQuantity;
        if (unfilled.IsZero)
        {
            // 全約定済み (ApplyAsync で既に Filled 遷移済みのはず)。終端マークだけ重複させない。
            return;
        }

        // 残数量あり = キャンセル/失効/拒否 として扱う。
        order.MarkTerminated(OrderState.Cancelled, reason, _clock.UtcNow);
        await _orderRepo.UpdateAsync(order, ct);

        if (order.BrokerOrderId is not null)
        {
            _pendingTracker.Untrack(order.BrokerOrderId.Value);
        }

        // ExitOrder の場合は未約定枚数分の Position 予約 (HoldQty) を解放する。
        if (order.TradeType == TradeType.ExitOrder && order.TargetExecutionId is not null)
        {
            var position = await _positionRepo.FindByIdAsync(order.TargetExecutionId, ct);
            if (position is not null && !position.IsClosed)
            {
                try
                {
                    position.ReleaseReservation(unfilled);
                    await _positionRepo.UpdateAsync(position, ct);
                    _logger.LogInformation(
                        "建玉予約を解放: position={Pos} qty={Qty} (注文キャンセル/失効)",
                        position.Id, unfilled);
                }
                catch (InvalidOperationException ex)
                {
                    _logger.LogWarning(ex,
                        "建玉予約解放に失敗: position={Pos} qty={Qty}",
                        position.Id, unfilled);
                }
            }
        }
    }

    private async Task OpenPositionAsync(Order order, ExecutionEvent execution, CancellationToken ct)
    {
        var position = new Position(
            id: execution.ExecutionId,
            brokerCode: order.BrokerCode,
            strategy: order.Strategy,
            interval: order.Interval,
            tradeMode: order.TradeMode,
            symbol: execution.Symbol,
            side: execution.Side,
            initialQuantity: execution.Quantity,
            entryPrice: execution.Price,
            openedAtUtc: execution.ExecutedAt);
        await _positionRepo.AddAsync(position, ct);

        // 自動取引建玉のメタデータを永続化 (再起動時の Reconciliation で復元するため)
        if (order.TradeMode == TradeMode.Auto)
        {
            await _autoStore.UpsertAsync(new Sync.AutoPositionMetadata
            {
                ExecutionId = execution.ExecutionId.Value,
                BrokerCode = order.BrokerCode.Value,
                Strategy = order.Strategy.Value,
                Interval = order.Interval,
                SymbolCode = execution.Symbol.Value,
                Side = execution.Side.ToString(),
                OpenedAt = execution.ExecutedAt
            }, ct);
        }

        _logger.LogInformation(
            "Position opened: id={PositionId} side={Side} qty={Qty} entry={Entry}",
            position.Id, position.Side, position.LeaveQuantity, position.EntryPrice);
    }

    private async Task CloseTargetPositionAsync(ExecutionEvent execution, CancellationToken ct)
    {
        if (execution.TargetPositionId is null)
        {
            _logger.LogError(
                "ExitOrder ExecutionEvent has no TargetPositionId: execId={ExecId}",
                execution.ExecutionId);
            return;
        }

        var position = await _positionRepo.FindByIdAsync(execution.TargetPositionId, ct);
        if (position is null)
        {
            _logger.LogWarning(
                "ExitOrder target position not found: target={Target} execId={ExecId}",
                execution.TargetPositionId, execution.ExecutionId);
            return;
        }

        try
        {
            position.ApplyClosure(execution.Quantity, execution.ExecutedAt);
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogError(ex,
                "ApplyClosure failed: position={PositionId} qty={Qty}",
                position.Id, execution.Quantity);
            return;
        }

        if (position.IsClosed)
        {
            await _positionRepo.RemoveAsync(position.Id, ct);
            // メタデータも削除 (建玉消滅と同期)
            await _autoStore.RemoveAsync(position.Id.Value, ct);
            _logger.LogInformation("Position closed and removed: id={PositionId}", position.Id);
        }
        else
        {
            await _positionRepo.UpdateAsync(position, ct);
            _logger.LogInformation(
                "Position partially closed: id={PositionId} leave={Leave} hold={Hold}",
                position.Id, position.LeaveQuantity, position.HoldQuantity);
        }
    }
}
