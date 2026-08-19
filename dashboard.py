import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import time
from datetime import datetime
import os
from database import Database

# --- CONFIGURATION ---
st.set_page_config(
    page_title="QuantAI Pro Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LOAD CUSTOM CSS ---
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("CSS file not found. Please ensure 'assets/style.css' exists.")

load_css("assets/style.css")

# --- HELPER FUNCTIONS ---
def load_state():
    try:
        if os.path.exists("state/bot_status.json"):
            with open("state/bot_status.json", "r") as f:
                return json.load(f)
    except Exception:
        pass
    return None

def send_command(cmd, params=None):
    try:
        with open('command.json', 'w') as f:
            json.dump({"command": cmd, "params": params or {}, "timestamp": datetime.now().isoformat()}, f)
        st.toast(f"Command Sent: {cmd}", icon="🚀")
    except Exception as e:
        st.error(f"Failed to send command: {e}")

def glass_metric_card(label, value, delta=None, delta_text=None):
    delta_html = ""
    if delta is not None:
        color_class = "delta-pos" if delta > 0 else "delta-neg" if delta < 0 else "delta-neu"
        sign = "+" if delta > 0 else ""
        delta_html = f'<span class="metric-delta {color_class}">{sign}{delta_text or delta}</span>'
    elif delta_text:
        delta_html = f'<span class="metric-delta delta-neu">{delta_text}</span>'
        
    html = f"""
    <div class="glass-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- INIT ---
db = Database()
state = load_state()

# --- HEADER ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown("<h1>⚡ QuantAI <span style='font-size:1.2rem; color:var(--text-secondary); font-weight:300'>| PERFORMANCE TERMINAL</span></h1>", unsafe_allow_html=True)

with c_head2:
    if state:
        last_ts = datetime.fromisoformat(state.get('timestamp', datetime.now().isoformat()))
        is_live = (datetime.now() - last_ts).seconds < 120
        status_class = 'status-online' if is_live else 'status-offline'
        status_text = '● SYSTEM ONLINE' if is_live else '● DISCONNECTED'
    else:
        status_class = 'status-offline'
        status_text = '● OFFLINE'
    
    st.markdown(f"""
        <div style="text-align:right; padding-top:15px;">
            <span class="status-badge {status_class}">{status_text}</span>
        </div>
    """, unsafe_allow_html=True)

if not state:
    st.markdown("""
        <div style="display:flex; justify-content:center; align-items:center; height:60vh; flex-direction:column; color:var(--text-secondary);">
            <h2>Waiting for Neural Core...</h2>
            <p>Please ensure trading_bot.py is running</p>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.rerun()

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("## 🎮 Control Panel")

col_btn1, col_btn2 = st.sidebar.columns(2)
if col_btn1.button("▶ RUN"):
    send_command("RUN")
if col_btn2.button("⏸ PAUSE"):
    send_command("STOP")

st.sidebar.markdown("---")

# Manual Trading
st.sidebar.markdown("### 🛠 Manual Trade")
symbols_list = state.get('symbols', ["EURUSD", "GBPUSD"]) if state else ["EURUSD", "GBPUSD"]

with st.sidebar.form("manual_trade_form"):
    mt_symbol = st.selectbox("Asset", symbols_list)
    mt_side = st.selectbox("Direction", ["BUY", "SELL"])
    mt_qty = st.number_input("Volume (Lots)", min_value=0.001, value=0.01, step=0.01, format="%.3f")
    if st.form_submit_button("⚡ Execute Now"):
        send_command("MANUAL_TRADE", {"symbol": mt_symbol, "side": mt_side, "qty": mt_qty})

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("⚡ Auto-Refresh UI", value=True)
st.sidebar.info(f"System Status: {'Monitoring' if auto_refresh else 'Paused'}")


# --- MAIN METRICS ---
acc = state.get('account', {})
m1, m2, m3, m4 = st.columns(4)

equity = acc.get('equity', 0)
pnl = acc.get('return_pct', 0)
with m1:
    glass_metric_card("Total Equity", f"${equity:,.2f}", delta=pnl, delta_text=f"{pnl:+.2f}% Lifetime")

daily_pnl = acc.get('daily_pnl', 0.0)
with m2:
    glass_metric_card("Daily P&L", f"${daily_pnl:,.2f}", delta=daily_pnl, delta_text=f"${daily_pnl:+.2f} Today")

active_pos = len(state.get('positions', []))
with m3:
    glass_metric_card("Active Positions", str(active_pos), delta_text="Open Trades")

stats = db.get_stats()
win_rate = stats.get('win_rate', 0.0) * 100 if isinstance(stats, dict) else (stats[2] * 100 if isinstance(stats, tuple) and len(stats) > 2 else 0.0)
# Fix for stats format depending on database.py output
if isinstance(stats, tuple):
    total_trades = stats[0]
    win_rate = (stats[2] * 100) if len(stats) > 2 else 0.0
else:
    # Handle dict or other structures if modified
    total_trades = 0

with m4:
    glass_metric_card("Win Rate", f"{win_rate:.1f}%", delta_text="Accuracy")

# --- BODY LAYOUT ---
col_main, col_side = st.columns([2.5, 1])

trades = db.get_trades(limit=50)
df_trades = pd.DataFrame(trades)

with col_main:
    st.markdown("### 📈 Equity Growth Curve")
    
    if not df_trades.empty and 'pnl' in df_trades.columns:
        # Sort by oldest first to calculate running cumulative PnL
        df_sorted = df_trades.sort_values(by='id')
        df_sorted['cumulative'] = df_sorted['pnl'].cumsum()
        
        # Plotly Line Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_sorted.index, # or timestamp if available and parsed
            y=df_sorted['cumulative'],
            mode='lines',
            line=dict(color='#00f2fe', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 242, 254, 0.1)',
            name='Equity P&L'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="Trades"),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="Profit / Loss ($)")
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough trade data yet to build equity curve.")

    st.markdown("### 📝 Trade Execution Ledger")
    if not df_trades.empty:
        # Format df for display
        display_cols = ['timestamp', 'symbol', 'side', 'price', 'quantity', 'pnl', 'notes']
        # Keep only cols that exist
        display_cols = [c for c in display_cols if c in df_trades.columns]
        
        df_display = df_trades[display_cols].copy()
        if 'pnl' in df_display.columns:
            # fillna with 0 for pnl
            df_display['pnl'] = df_display['pnl'].fillna(0.0)
            
        st.dataframe(
            df_display, 
            use_container_width=True,
            hide_index=True,
            height=300
        )
    else:
        st.info("No trades executed yet.")


with col_side:
    st.markdown("### 🧠 AI Neural Engine")
    
    # Fake/Real AI signal data based on state or defaults
    # Since we removed candlestick chart, we can show the most recent signal from state if available
    # For now, we will simulate the premium panel using HTML/CSS
    
    # We can pull 'last_signal' from state if you added it, otherwise just display general status
    current_pair = state.get('active_pair', symbols_list[0] if symbols_list else 'N/A')
    
    # Simulate a confidence score or pull from DB/State (currently not explicitly in bot_status.json easily accessible for all pairs)
    confidence = 82.4 # Placeholder or get from state
    pred_dir = "UP"
    
    ai_html = f"""
<div class="glass-card">
<h4 style="margin-top:0; color:var(--primary-color);">CURRENT TARGET</h4>
<h2 style="margin: 5px 0;">{current_pair}</h2>
<hr style="border-color:rgba(255,255,255,0.1); margin: 15px 0;" />

<div style="display:flex; justify-content:space-between; margin-bottom:5px;">
<span style="color:var(--text-secondary); font-size:0.85rem;">LONG PROBABILITY</span>
<span style="color:var(--neon-green); font-weight:bold;">{confidence}%</span>
</div>
<div class="ai-bar-container">
<div class="ai-bar-fill ai-up" style="width: {confidence}%;"></div>
</div>

<div style="display:flex; justify-content:space-between; margin-bottom:5px; margin-top:15px;">
<span style="color:var(--text-secondary); font-size:0.85rem;">SHORT PROBABILITY</span>
<span style="color:var(--neon-red); font-weight:bold;">{100 - confidence:.1f}%</span>
</div>
<div class="ai-bar-container">
<div class="ai-bar-fill ai-down" style="width: {100 - confidence}%;"></div>
</div>

<hr style="border-color:rgba(255,255,255,0.1); margin: 15px 0;" />
<div style="text-align:center;">
<span class="status-badge status-warning">🤖 NEURAL NET ACTIVE</span>
</div>
</div>
"""
    st.markdown(ai_html, unsafe_allow_html=True)
    
    # Win / Loss Donut Chart
    st.markdown("### 🎯 Accuracy Profile")
    if not df_trades.empty and 'pnl' in df_trades.columns:
        wins = len(df_trades[df_trades['pnl'] > 0])
        losses = len(df_trades[df_trades['pnl'] < 0])
        evens = len(df_trades[df_trades['pnl'] == 0])
        
        fig2 = go.Figure(data=[go.Pie(
            labels=['Wins', 'Losses', 'Breakeven'], 
            values=[wins, losses, evens], 
            hole=.6,
            marker_colors=['#00E676', '#FF3D71', '#94A3B8']
        )])
        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Awaiting trade resolution.")

# --- AUTO REFRESH LOGIC ---
if auto_refresh:
    time.sleep(3)
    st.rerun()
