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
    page_title="Performance Summary",
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
        st.error("CSS file not found.")

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

def flat_metric_card(label, value, delta=None, delta_text=None):
    delta_html = ""
    if delta is not None:
        color_class = "delta-pos" if delta > 0 else "delta-neg" if delta < 0 else "delta-neu"
        sign = "+" if delta > 0 else ""
        delta_html = f'<span class="metric-delta {color_class}">{sign}{delta_text or delta}</span>'
    elif delta_text:
        delta_html = f'<span class="metric-delta delta-neu">{delta_text}</span>'
        
    html = f"""
    <div class="flat-card" style="padding:15px;">
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
st.markdown("<h2 style='font-weight:400; font-size:1.4rem; color:var(--text-primary);'>&larr; Performance summary</h2>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- TOP METRICS ROW ---
m1, m2, m3, m4 = st.columns(4)
acc = state.get('account', {}) if state else {}

initial_cap = 10000  # Default or fetch from config
equity = acc.get('equity', 0)
daily_pnl = acc.get('daily_pnl', 0.0)
active_pos = len(state.get('positions', [])) if state else 0

stats = db.get_stats()
if isinstance(stats, tuple):
    total_trades = stats[0]
    win_rate = (stats[2] * 100) if len(stats) > 2 else 0.0
else:
    win_rate = stats.get('win_rate', 0.0) * 100 if isinstance(stats, dict) else 0.0

with m1:
    # "Portfolio - start state" equivalent
    flat_metric_card("Initial Capital", f"${initial_cap:,.2f}")
with m2:
    # "Portfolio - end state" equivalent
    flat_metric_card("Total Equity", f"${equity:,.2f}", delta=daily_pnl, delta_text=f"${daily_pnl:+.2f} Today")
with m3:
    # "Health factor" equivalent
    flat_metric_card("Active Trades", str(active_pos), delta_text="Open Positions")
with m4:
    # "Portfolio evolution" equivalent
    flat_metric_card("Win Rate", f"{win_rate:.1f}%", delta=win_rate-50, delta_text="Accuracy")


# --- MAIN SPLIT LAYOUT ---
st.markdown("<br>", unsafe_allow_html=True)
col_left, col_right = st.columns([1.6, 1])

trades = db.get_trades(limit=50)
df_trades = pd.DataFrame(trades)

with col_left:
    st.markdown(f"""
    <div style="margin-bottom:15px; padding-left:15px;">
        <div class="current-balance-label">Current balance</div>
        <div class="current-balance-val">${equity:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Smooth Equity Curve (Electric Blue)
    if not df_trades.empty and 'pnl' in df_trades.columns:
        # Ensure we have a proper datetime index for the x-axis
        if 'timestamp' in df_trades.columns:
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'], errors='coerce')
            df_sorted = df_trades.dropna(subset=['timestamp']).sort_values(by='timestamp').copy()
            df_sorted.set_index('timestamp', inplace=True)
        else:
            df_sorted = df_trades.copy()

        # Handle NaNs in PnL
        df_sorted['pnl'] = pd.to_numeric(df_sorted['pnl'], errors='coerce').fillna(0.0)
        df_sorted['cumulative'] = df_sorted['pnl'].cumsum() + initial_cap
        
        # We need at least a starting point to draw a line properly
        if len(df_sorted) > 0:
            # Prepend starting capital to make the line start from the beginning
            start_time = df_sorted.index[0] - pd.Timedelta(minutes=5) if isinstance(df_sorted.index, pd.DatetimeIndex) else -1
            start_row = pd.DataFrame({'cumulative': [initial_cap]}, index=[start_time])
            df_plot = pd.concat([start_row, df_sorted[['cumulative']]])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_plot.index,
                y=df_plot['cumulative'],
                mode='lines',
                line=dict(color='#4C7CFF', width=3, shape='spline'), # Spline for smooth curve like template
                fill='tozeroy',
                fillcolor='rgba(76, 124, 255, 0.05)', # Very faint gradient
                name='Portfolio Value'
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0),
                height=300,
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.03)', tickfont=dict(color='#8A94A6', family='JetBrains Mono'))
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid trade timestamps found.")
    else:
        st.info("Not enough trade data yet to build equity curve.")

with col_right:
    st.markdown("<div style='font-size:0.9rem; color:var(--text-secondary); margin-bottom:15px;'>Strategy Diagnostics</div>", unsafe_allow_html=True)
    
    # Dual Donut Charts (Matching Template)
    # 1. Win/Loss Ratio, 2. AI Confidence
    c_donut1, c_donut2 = st.columns(2)
    
    # Chart 1: Win Rate Donut
    wins = len(df_trades[df_trades['pnl'] > 0]) if not df_trades.empty and 'pnl' in df_trades.columns else 0
    losses = len(df_trades[df_trades['pnl'] <= 0]) if not df_trades.empty and 'pnl' in df_trades.columns else 1 # Avoid div by zero visual
    
    fig_win = go.Figure(data=[go.Pie(
        labels=['Wins', 'Losses'], 
        values=[max(wins, 0.1), max(losses, 0.1)], # Fake small value just to draw circle if empty
        hole=.75,
        marker_colors=['#00E676', '#FF3D71'] if wins > 0 else ['#2a3241', '#2a3241'],
        textinfo='none'
    )])
    fig_win.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=20), height=180, showlegend=False,
        annotations=[dict(text='Win Rate', x=0.5, y=0.6, font_size=10, font_color='#8A94A6', showarrow=False),
                     dict(text=f"{win_rate:.0f}%", x=0.5, y=0.4, font_size=20, font_color='#FFFFFF', showarrow=False)]
    )
    
    # Chart 2: AI Confidence Donut
    confidence = 82.4 # Pull from state if available
    fig_conf = go.Figure(data=[go.Pie(
        labels=['Confidence', 'Uncertainty'], 
        values=[confidence, 100-confidence], 
        hole=.75,
        marker_colors=['#4C7CFF', '#2a3241'],
        textinfo='none'
    )])
    fig_conf.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=20), height=180, showlegend=False,
        annotations=[dict(text='Confidence', x=0.5, y=0.6, font_size=10, font_color='#8A94A6', showarrow=False),
                     dict(text=f"{confidence}%", x=0.5, y=0.4, font_size=20, font_color='#FFFFFF', showarrow=False)]
    )
    
    with c_donut1:
        st.plotly_chart(fig_win, use_container_width=True)
    with c_donut2:
        st.plotly_chart(fig_conf, use_container_width=True)
        
    # Extra diagnostics text below donuts
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-top:20px;">
        <div><span style="color:var(--accent-green)">●</span> Total Wins: {wins}</div>
        <div><span style="color:var(--accent-red)">●</span> Total Losses: {losses}</div>
    </div>
    """, unsafe_allow_html=True)

# --- TRADE LEDGER (BOTTOM TABLE) ---
st.markdown("<br><hr style='border-color:var(--card-border);'>", unsafe_allow_html=True)
st.markdown("<h4 style='font-size:1rem; margin-bottom:15px;'>Recent Actions</h4>", unsafe_allow_html=True)

if not df_trades.empty:
    display_cols = ['timestamp', 'symbol', 'side', 'price', 'quantity', 'pnl']
    display_cols = [c for c in display_cols if c in df_trades.columns]
    
    df_display = df_trades[display_cols].copy()
    
    # Format table for sleek styling
    if 'pnl' in df_display.columns:
        df_display['pnl'] = df_display['pnl'].fillna(0.0)
        # We can't perfectly color text inside st.dataframe without styling, 
        # so we rely on the custom CSS we wrote for the dataframe borders.
    
    st.dataframe(
        df_display, 
        use_container_width=True,
        hide_index=True,
        height=250
    )
else:
    st.info("No actions logged yet.")

# --- SIDEBAR (HIDDEN OR MINIMAL) ---
st.sidebar.markdown("### 🎮 Quick Actions")
if st.sidebar.button("▶ RUN BOT"):
    send_command("RUN")
if st.sidebar.button("⏸ PAUSE BOT"):
    send_command("STOP")

# System Terminal in sidebar for debug view
st.sidebar.markdown("---")
st.sidebar.markdown("### 🖥️ Terminal")
logs = state.get('latest_logs', []) if state else []
log_text = "".join(logs) if logs else "No logs available."
st.sidebar.markdown(f"""
<div class="system-terminal">
    <pre>{log_text}</pre>
</div>
""", unsafe_allow_html=True)

# --- AUTO REFRESH LOGIC ---
if st.sidebar.checkbox("⚡ Auto-Refresh UI", value=True):
    time.sleep(5)
    st.rerun()
