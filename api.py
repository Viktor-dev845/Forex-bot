from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from database import Database
import json
import os

app = Flask(__name__, static_folder='frontend', static_url_path='/')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

db = Database()

def load_state():
    try:
        if os.path.exists("state/bot_status.json"):
            with open("state/bot_status.json", "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def get_stats_data():
    state = load_state()
    weekly_pnl = db.get_weekly_pnl()
    
    acc = state.get('account', {})
    equity = acc.get('equity', 0)
    daily_pnl = acc.get('daily_pnl', 0.0)
    active_pos = len(state.get('positions', [])) if state.get('positions') else 0
    
    stats = db.get_stats()
    if isinstance(stats, tuple):
        win_rate = (stats[2] * 100) if len(stats) > 2 else 0.0
    else:
        win_rate = stats.get('win_rate', 0.0) * 100 if isinstance(stats, dict) else 0.0

    return {
        "equity": equity,
        "daily_pnl": daily_pnl,
        "weekly_pnl": weekly_pnl,
        "target": 100.0,
        "active_positions": active_pos,
        "win_rate": win_rate,
        "state": state
    }

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/stats')
def get_stats():
    return jsonify(get_stats_data())

@app.route('/api/trades')
def get_trades():
    trades = db.get_trades(limit=50)
    return jsonify(trades)

@app.route('/api/internal/notify', methods=['POST'])
def internal_notify():
    """Webhook for the bot to notify that data has changed."""
    stats = get_stats_data()
    trades = db.get_trades(limit=50)
    socketio.emit('dashboard_update', {'stats': stats, 'trades': trades})
    return jsonify({"status": "success"})

@socketio.on('connect')
def handle_connect():
    # Send immediate data on connect
    stats = get_stats_data()
    trades = db.get_trades(limit=50)
    socketio.emit('dashboard_update', {'stats': stats, 'trades': trades}, to=request.sid)

if __name__ == '__main__':
    # Run with socketio
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
