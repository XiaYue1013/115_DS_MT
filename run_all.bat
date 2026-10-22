@echo off
REM Windows cmd：直接雙擊或執行 run_all.bat；實際工作交給 run_all.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all.ps1" %*
pause
