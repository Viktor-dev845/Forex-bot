@echo off
title QuantAI Trading Bot & Dashboard

echo ==================================================
echo   Starting QuantAI Performance Dashboard...
echo ==================================================
:: Run streamlit using python module to avoid PATH issues
start /B python -m streamlit run dashboard.py

echo.
echo ==================================================
echo   Starting QuantAI Neural Engine...
echo ==================================================
:: Run the trading bot in the foreground
python trading_bot.py

pause
