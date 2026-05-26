@echo off
REM N225BrokerBridge Dashboard B launcher - launches via pythonw.exe (no console)

cd /d "%~dp0"

set "VENV_PYTHONW=%~dp0N225SignalTrader\.venv\Scripts\pythonw.exe"
set "DASHBOARD=%~dp0n225_brokerbridge_dashboard.py"

if not exist "%VENV_PYTHONW%" (
    echo ERROR: pythonw.exe not found
    echo Path: %VENV_PYTHONW%
    pause
    exit /b 1
)

if not exist "%DASHBOARD%" (
    echo ERROR: n225_brokerbridge_dashboard.py not found
    echo Path: %DASHBOARD%
    pause
    exit /b 1
)

start "" "%VENV_PYTHONW%" "%DASHBOARD%"
exit /b 0
