import json
import os
import time
import threading
import sqlite3

class StateReader:
    """Reads bot state from JSON and SQLite without locking the files."""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.status_file = os.path.join(self.base_dir, "state", "bot_status.json")
        self.metrics_file = os.path.join(self.base_dir, "logs", "metrics.json")
        self.db_path = os.path.join(self.base_dir, "trading_bot.db")
        
        self.current_state = {}
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()

    def _read_loop(self):
        while self.running:
            try:
                if os.path.exists(self.status_file):
                    with open(self.status_file, 'r') as f:
                        self.current_state = json.load(f)
            except Exception:
                pass
            time.sleep(0.5)

    def get_bot_state(self):
        return self.current_state

    def get_recent_trades(self, limit=50):
        try:
            if not os.path.exists(self.db_path):
                return []
                
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Use 'trade_journal' instead of 'trades'
            cursor.execute('''
                SELECT * FROM trade_journal 
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
            
            trades = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return trades
        except Exception as e:
            print(f"Error reading DB: {e}")
            return []

    def get_metrics(self):
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
