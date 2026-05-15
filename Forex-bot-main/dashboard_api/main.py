from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import os
import sqlite3
from datetime import datetime

from state_reader import StateReader
from candle_provider import CandleProvider

app = FastAPI(title="QuantAI Dashboard API")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state_reader = StateReader()
candle_provider = CandleProvider()

# Connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Background task to broadcast live data
async def broadcast_live_data():
    while True:
        try:
            # Broadcast state
            state = state_reader.get_bot_state()
            if state:
                await manager.broadcast(json.dumps({
                    "type": "state_update",
                    "data": state
                }))
            
            # Broadcast latest tick for active symbol
            ticks = candle_provider.get_latest_ticks()
            if ticks:
                await manager.broadcast(json.dumps({
                    "type": "tick_update",
                    "data": ticks
                }))
                
        except Exception as e:
            print(f"Broadcast error: {e}")
            
        await asyncio.sleep(1) # Broadcast every 1s

@app.on_event("startup")
async def startup_event():
    # Start the state reader
    state_reader.start()
    # Start the candle provider in background so API stays responsive
    asyncio.create_task(candle_provider.connect())
    # Start broadcast loop
    asyncio.create_task(broadcast_live_data())

@app.on_event("shutdown")
async def shutdown_event():
    await candle_provider.disconnect()

# REST Endpoints
@app.get("/api/status")
async def get_status():
    return state_reader.get_bot_state()

@app.get("/api/trades")
async def get_trades(limit: int = 50):
    return state_reader.get_recent_trades(limit)

@app.get("/api/metrics")
async def get_metrics():
    return state_reader.get_metrics()

@app.get("/api/candles/{symbol}/{timeframe}")
async def get_candles(symbol: str, timeframe: str = "M5"):
    # Returns history + streaming format compatible with TradingView
    return await candle_provider.get_history(symbol, timeframe)

@app.post("/api/command")
async def send_command(command: dict):
    cmd_file = os.path.join(os.path.dirname(__file__), "..", "command.json")
    try:
        # We use a simple lock via rename to prevent the race condition found in Bug 6.3
        import tempfile
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(cmd_file))
        with os.fdopen(fd, 'w') as f:
            json.dump({
                "command": command.get("command"),
                "params": command.get("params", {}),
                "timestamp": datetime.now().isoformat()
            }, f)
        os.replace(temp_path, cmd_file) # Atomic rename on POSIX/NTFS
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# WebSocket Endpoint
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
