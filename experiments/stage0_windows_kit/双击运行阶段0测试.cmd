@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all.ps1"
echo.
echo 结果已写入 results 目录，按任意键退出。
pause >nul
