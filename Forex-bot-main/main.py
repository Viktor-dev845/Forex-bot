import asyncio
import os
import sys
from datetime import datetime
import logging

# Add the project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot import TradingBot
from utils.config_loader import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/main_execution.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Main")

async def main():
    print("""
    ==================================================
    INSTITUTIONAL AI TRADING BOT - HARDENED VERSION
    ==================================================
    Target Accuracy: 80-90% (Volatility 75 Specialist)
    Account Protection: Active (10% Circuit Breaker)
    Execution Mode: Smart Async Loop (Ticking 1s)
    ==================================================
    """)
    
    # 1. Load Config
    if not os.path.exists('config.json'):
        logger.error("config.json not found! Please create it.")
        return
        
    config = load_config()
    
    # 2. Safety Check
    is_paper = config.get('bot', {}).get('paper_trading', True)
    if not is_paper:
        confirm = input("⚠️ WARNING: LIVE TRADING DETECTED. Type 'CONFIRM' to proceed: ")
        if confirm != 'CONFIRM':
            print("Safe abort.")
            return

    # 3. Initialize Bot
    try:
        bot = TradingBot(config)
        
        # 4. Start the Engine
        logger.info(f"Bot starting for {config['markets']['synthetics']['symbols']}...")
        await bot.start()
        
    except Exception as e:
        logger.critical(f"FATAL ERROR ON STARTUP: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
