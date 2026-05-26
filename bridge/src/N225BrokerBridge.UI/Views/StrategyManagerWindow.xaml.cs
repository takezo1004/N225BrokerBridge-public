using System.Windows;
using Microsoft.Extensions.Logging;
using N225BrokerBridge.UI.ViewModels;
using Wpf.Ui.Controls;

namespace N225BrokerBridge.UI.Views;

public partial class StrategyManagerWindow : FluentWindow
{
    private readonly ILogger<StrategyManagerWindow>? _logger;

    public StrategyManagerWindow(StrategyManagerViewModel vm, ILogger<StrategyManagerWindow> logger)
    {
        InitializeComponent();
        DataContext = vm;
        _logger = logger;
        _logger.LogInformation("StrategyManagerWindow opened");
    }

    private void OnCloseClicked(object sender, RoutedEventArgs e)
    {
        _logger?.LogInformation("StrategyManagerWindow: Close button clicked");
        // ShowDialog 経由で開かれているため DialogResult を明示してから Close する。
        // これがないと一部の FluentWindow 派生で Close() が無視されることがある。
        try { DialogResult = false; } catch { /* not modal */ }
        Close();
    }
}
