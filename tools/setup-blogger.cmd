@echo off
chcp 65001 >nul
title Blogger Setup
"C:\Program Files\Git\bin\bash.exe" -l /c/Projects/Agent-site/tools/setup-blogger.sh
echo.
if errorlevel 1 echo 設定因錯誤而停止。
echo 視窗會保持開啟，方便你查看結果。
pause
