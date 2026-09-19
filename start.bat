@echo off
title "QuantAI Trading Bot & Dashboard"

echo ==================================================
echo   Starting QuantAI Web API...
echo ==================================================
:: Run the Flask API server in the background and hide output
start /B python api.py > api.log 2>&1

echo.
echo ==================================================
echo   Starting QuantAI Neural Engine...
echo ==================================================
:restart
:: Run the trading bot in the foreground
python -u trading_bot.py

echo.
echo [WARNING] Connection lost or bot stopped. Auto-restarting in 10 seconds...
timeout /t 10
goto restart
