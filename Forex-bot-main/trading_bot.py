import logging
import json
import time
import os
import sys
import asyncio
from datetime import datetime
import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None

from strategies.risk_manager import RiskManager
from strategies.order_executor import OrderExecutor, OrderSide, OrderStatus, PaperTradingExecutor
from utils.retrainer import RetrainingManager
from strategy_engine import AIStrategy, EnsembleStrategy, TradeAction
from utils.data_loader import fetch_historical_data, save_data, fetch_data_mt5
from utils.monitoring import BotMonitor, TradeRecord
from models.lstm_model import TradingLSTM
from ai_model import ForexModel
from feature_engine import FeatureEngine
from meta_labeller import MetaLabeller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingBot:
    # Deriv symbol mapping: Internal name -> API Ticker
    SYMBOL_MAP = {
        'Volatility 75 Index': 'R_75',
        'Crash 500 Index': 'CRASH500',
        'Boom 1000 Index': 'BOOM1000',
        'Volatility 100 Index': 'R_100',
        'Crash 1000 Index': 'CRASH1000'
    }

    def __init__(self, config: dict):
        self.config = config
        self.monitor = BotMonitor(log_dir="logs")
        self.monitor.logger.info("Initializing Hardened Trading Bot...")
        
        self.market_type = config.get('bot', {}).get('market_type', 'forex')
        self.symbols = config.get('markets', {}).get(self.market_type, {}).get('symbols', [])
        
        # Risk Setup
        from strategies.risk_manager import RiskParameters
        risk_params = RiskParameters(
            risk_per_trade_pct=0.015,
            max_daily_loss_pct=0.10,
            max_open_positions=1,
            min_confidence=0.60
        )
        self.risk_manager = RiskManager(risk_params)
        
        if config.get('bot', {}).get('paper_trading', True):
            self.executor = PaperTradingExecutor(initial_capital=100)
        else:
            from strategies.order_executor import MT5Executor
            mt5_cfg = config.get('brokers', {}).get('mt5', {})
            self.executor = MT5Executor(login=int(mt5_cfg['login']), password=mt5_cfg['password'], server=mt5_cfg['server']) 
        
        self.token = config.get('brokers', {}).get('deriv', {}).get('api_token')
        
        self.fe = FeatureEngine()
        self.models = {}
        for symbol in self.symbols:
            self.models[symbol] = {'lstm': self._load_model('lstm', symbol)}
            
        self.last_analysis_minute = -1 
        self.trade_lock = asyncio.Lock()
        self.positions = {symbol: None for symbol in self.symbols}
        self.entry_prices = {symbol: 0 for symbol in self.symbols}
        self.daily_pnl = 0.0

        # WebSocket Streaming
        self.websocket_client = None
        if config.get('websocket', {}).get('enabled', False):
            from websocket_client import DerivWebSocketClient
            self.websocket_client = DerivWebSocketClient(self.symbols, api_token=self.token)
            self.websocket_client.connect()

    def _load_model(self, model_type: str, symbol: str):
        if model_type == 'lstm':
            model_path = f"models/{symbol}_lstm.pth"
            if os.path.exists(model_path):
                import torch
                checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
                input_size = checkpoint.get('input_size', 57)
                model = TradingLSTM(input_size=input_size)
                model.load_state_dict(checkpoint['model_state_dict'])
                model.eval()
                return model
        return None

    def run_trading_cycle(self):
        self.monitor.logger.info("Cycle Started: Scanning for setups...")
        
        try:
            from data_loader import fetch_historical_data
            data_map = {}
            for s in self.symbols:
                # FIX: Map 'Volatility 75 Index' -> 'R_75' for API call
                api_ticker = self.SYMBOL_MAP.get(s, s)
                df = asyncio.run(fetch_historical_data(api_ticker, time_interval="5m", max_candles=300))
                if df is not None: data_map[s] = df
            
            if not data_map: return
        except Exception as e:
            self.monitor.logger.error(f"Fetch Error: {e}")
            return

        for symbol, df in data_map.items():
            if df is None or len(df) < 30: continue
            
            features = self.fe.generate_features(df.copy())
            if features.empty: continue
            
            import torch
            expected_size = self.models[symbol]['lstm'].lstm.input_size
            feat_vals = features.values
            if feat_vals.shape[1] > expected_size: feat_vals = feat_vals[:, :expected_size]
            
            seq = torch.FloatTensor(feat_vals[-30:]).unsqueeze(0)
            prob = torch.sigmoid(self.models[symbol]['lstm'](seq)).item()
            
            self.monitor.logger.info(f"[{symbol}] AI Confidence: {prob:.2%}")
            
            if prob >= 0.60: self.execute_trade(symbol, TradeAction.GO_LONG, df['Close'].iloc[-1], df)
            elif prob <= 0.40: self.execute_trade(symbol, TradeAction.GO_SHORT, df['Close'].iloc[-1], df)

    def execute_trade(self, symbol, action, price, df):
        if self.positions[symbol]: return
        
        qty = self.risk_manager.calculate_forex_position_size(100 + self.daily_pnl, symbol, df['Close'].diff().abs().mean())
        side = OrderSide.BUY if action == TradeAction.GO_LONG else OrderSide.SELL
        
        order = self.executor.submit_order(symbol, side, qty)
        if order and order.status == OrderStatus.FILLED:
            self.positions[symbol] = {'side': 'long' if side==OrderSide.BUY else 'short', 'qty': qty}
            self.entry_prices[symbol] = price
            self.monitor.logger.info(f"✅ TRADE PLACED: {side.value} {symbol} @ {price}")

    async def start(self):
        self.monitor.logger.info("Bot logic active.")
        await asyncio.to_thread(self.run_trading_cycle)
        while True:
            now = datetime.now()
            if now.minute % 5 == 0 and now.minute != self.last_analysis_minute:
                async with self.trade_lock:
                    await asyncio.to_thread(self.run_trading_cycle)
                    self.last_analysis_minute = now.minute
            await asyncio.sleep(1)

if __name__ == "__main__":
    from utils.config_loader import load_config
    bot = TradingBot(load_config())
    asyncio.run(bot.start())
