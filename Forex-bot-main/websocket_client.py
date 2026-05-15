"""
WebSocket Client for Real-Time Price Streaming
Hardened for Institutional Reliability.
"""

import asyncio
import json
import logging
import threading
import time
from typing import Dict, List, Optional
import websockets

logger = logging.getLogger(__name__)

class DerivWebSocketClient:
    SYMBOL_MAP = {
        'Volatility 75 Index': 'R_75',
        'Crash 500 Index': 'CRASH500',
        'Boom 1000 Index': 'BOOM1000',
        'R_75': 'R_75'
    }

    def __init__(self, symbols: List[str], api_token: Optional[str] = None):
        self.symbols = symbols
        self.api_token = api_token
        # Using a reliable public app_id
        self.ws_url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        self.prices: Dict[str, float] = {}
        self.price_lock = threading.Lock()
        self.running = False
        self.connected = False
        self.loop = None

    def connect(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._run_loop, daemon=True).start()
        
        # Wait for auth
        for _ in range(20):
            if self.connected: break
            time.sleep(0.5)

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._listen())

    async def _listen(self):
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # 1. AUTHORIZE FIRST (Critical)
                    if self.api_token:
                        await ws.send(json.dumps({"authorize": self.api_token}))
                        auth_res = await ws.recv()
                        auth_data = json.loads(auth_res)
                        if 'error' in auth_data:
                            logger.error(f"Auth Failed: {auth_data['error']['message']}")
                            self.connected = False
                            await asyncio.sleep(5)
                            continue
                        logger.info("Deriv Authenticated Successfully.")
                    
                    self.connected = True
                    # 2. SUBSCRIBE
                    for sym in self.symbols:
                        ticker = self.SYMBOL_MAP.get(sym, sym)
                        await ws.send(json.dumps({"ticks": ticker, "subscribe": 1}))
                    
                    async for msg in ws:
                        data = json.loads(msg)
                        if 'tick' in data:
                            t = data['tick']
                            with self.price_lock:
                                # Store by original name for bot compatibility
                                self.prices[sym] = float(t['quote'])
            except Exception as e:
                self.connected = False
                logger.error(f"WS Connection Lost: {e}")
                await asyncio.sleep(5)

    def get_latest_price(self, symbol: str):
        with self.price_lock: return self.prices.get(symbol)

    def is_connected(self): return self.connected
    def disconnect(self): self.running = False
