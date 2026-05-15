import asyncio
import os
from trading_bot import TradingBot
from utils.config_loader import load_config

async def run_once():
    config = load_config()
    bot = TradingBot(config)
    print("Running one-time trading cycle for:", bot.symbols)
    await asyncio.to_thread(bot.run_trading_cycle)
    print("Cycle complete. Check logs for details.")

if __name__ == "__main__":
    asyncio.run(run_once())
