@echo off
REM N225 Simulator Test Dashboard 起動
REM   - Bridge を --simulator で立ち上げ、Webhook ペイロード 7 種をボタンで発火
REM   - 詳細: n225_simulator_test_dashboard.py 冒頭の docstring 参照
cd /d "%~dp0"
python n225_simulator_test_dashboard.py
if errorlevel 1 (
    echo.
    echo Dashboard exited with error. Press any key to close.
    pause >nul
)
