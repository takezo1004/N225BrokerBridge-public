# TradingView (MSIX/Store版) を --remote-debugging-port=9222 付きで起動する
# IApplicationActivationManager COM API (C# Add-Type) を使用

Add-Type @"
using System;
using System.Runtime.InteropServices;

public class AppActivator
{
    [ComImport]
    [Guid("2e941141-7f97-4756-ba1d-9decde894a3d")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IApplicationActivationManager
    {
        uint ActivateApplication(
            [MarshalAs(UnmanagedType.LPWStr)] string appUserModelId,
            [MarshalAs(UnmanagedType.LPWStr)] string arguments,
            int options,
            out uint processId);
        uint ActivateForFile(
            [MarshalAs(UnmanagedType.LPWStr)] string appUserModelId,
            IntPtr itemArray,
            [MarshalAs(UnmanagedType.LPWStr)] string verb,
            out uint processId);
        uint ActivateForProtocol(
            [MarshalAs(UnmanagedType.LPWStr)] string appUserModelId,
            IntPtr itemArray,
            out uint processId);
    }

    [ComImport]
    [Guid("45BA127D-10A8-46EA-8AB7-56EA9078943C")]
    [CoClass(typeof(AppActivationManagerClass))]
    private interface CApplicationActivationManager : IApplicationActivationManager { }

    [ComImport]
    [Guid("45BA127D-10A8-46EA-8AB7-56EA9078943C")]
    private class AppActivationManagerClass { }

    public static uint Launch(string aumid, string arguments)
    {
        var manager = (IApplicationActivationManager)new AppActivationManagerClass();
        uint pid = 0;
        uint hr = manager.ActivateApplication(aumid, arguments, 0, out pid);
        if (hr != 0)
            throw new COMException("ActivateApplication failed", (int)hr);
        return pid;
    }
}
"@

$aumid = "TradingView.Desktop_n534cwy3pjxzj!TradingView.Desktop"
$debugArgs = "--remote-debugging-port=9222 --remote-allow-origins=*"

Write-Host "TradingView を終了中..."
Stop-Process -Name "TradingView" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

Write-Host "デバッグモードで起動中..."
Write-Host "AUMID: $aumid"

try {
    $tvPid = [AppActivator]::Launch($aumid, $debugArgs)
    Write-Host "起動成功: PID = $tvPid"
} catch {
    Write-Host "ERROR: $_"
    exit 1
}

Write-Host "CDP エンドポイント待機中..."
Start-Sleep -Seconds 8

for ($i = 0; $i -lt 10; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "CDP 接続成功!"
        $r.Content | ConvertFrom-Json | Format-List Browser, webSocketDebuggerUrl
        exit 0
    } catch {
        Write-Host "待機中... ($($i+1)/10)"
        Start-Sleep -Seconds 3
    }
}

Write-Host "ERROR: CDP エンドポイントが応答しませんでした"
exit 1
