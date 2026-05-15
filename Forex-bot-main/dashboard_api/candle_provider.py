import json
import asyncio
import websockets
from datetime import datetime

class CandleProvider:
    """Connects to Deriv WebSocket to stream live ticks and history for charts."""
    
    # Deriv symbols
    SYMBOL_MAP = {
        'Volatility 75 Index': 'R_75',
        'Crash 500 Index': 'CRASH500',
        'Boom 1000 Index': 'BOOM1000',
    }
    
    # Reverse map for broadcasting back to frontend
    REVERSE_SYMBOL_MAP = {v: k for k, v in SYMBOL_MAP.items()}
    
    def __init__(self):
        self.ws_url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        self.websocket = None
        self.connected = False
        self.latest_ticks = {}
        self.history_callbacks = {}
        self.request_id = 1
        
    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.connected = True
            asyncio.create_task(self._listen())
            
            # Subscribe to our 3 main symbols
            for symbol in self.SYMBOL_MAP.values():
                await self.websocket.send(json.dumps({
                    "ticks": symbol,
                    "subscribe": 1
                }))
        except Exception as e:
            print(f"CandleProvider WS error: {e}")
            
    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            
    async def _listen(self):
        while self.connected:
            try:
                msg = await self.websocket.recv()
                data = json.loads(msg)
                
                # Handle tick stream
                if 'tick' in data:
                    tick = data['tick']
                    sym = tick.get('symbol')
                    if sym:
                        self.latest_ticks[sym] = {
                            "time": tick.get('epoch'),
                            "price": tick.get('quote')
                        }
                
                # Handle history response
                elif 'history' in data:
                    req_id = data.get('req_id')
                    if req_id in self.history_callbacks:
                        self.history_callbacks[req_id].set_result(data['history'])
                        
            except Exception as e:
                print(f"CandleProvider listen error: {e}")
                await asyncio.sleep(1)

    def get_latest_ticks(self):
        # Map tickers (e.g. R_75) back to full names (e.g. Volatility 75 Index)
        return {self.REVERSE_SYMBOL_MAP.get(k, k): v for k, v in self.latest_ticks.items()}
        
    async def get_history(self, symbol_name: str, timeframe: str = "M5"):
        deriv_symbol = self.SYMBOL_MAP.get(symbol_name, symbol_name)
        
        # Convert timeframe to Deriv granularity (seconds)
        granularity = 300 # M5 default
        if timeframe == "M1": granularity = 60
        elif timeframe == "M15": granularity = 900
        elif timeframe == "H1": granularity = 3600
        
        req_id = self.request_id
        self.request_id += 1
        
        future = asyncio.get_event_loop().create_future()
        self.history_callbacks[req_id] = future
        
        await self.websocket.send(json.dumps({
            "ticks_history": deriv_symbol,
            "adjust_start_time": 1,
            "count": 500,
            "end": "latest",
            "style": "candles",
            "granularity": granularity,
            "req_id": req_id
        }))
        
        try:
            # Wait for response with timeout
            history = await asyncio.wait_for(future, timeout=5.0)
            
            # Format for TradingView Lightweight Charts
            formatted_candles = []
            if 'candles' in history:
                for c in history['candles']:
                    formatted_candles.append({
                        "time": c['epoch'],
                        "open": c['open'],
                        "high": c['high'],
                        "low": c['low'],
                        "close": c['close']
                    })
            
            del self.history_callbacks[req_id]
            return formatted_candles
            
        except asyncio.TimeoutError:
            del self.history_callbacks[req_id]
            return []
