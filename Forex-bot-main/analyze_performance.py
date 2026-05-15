import json
import pandas as pd
import os
from datetime import datetime

def analyze_performance():
    journal_path = 'logs/trade_journal.json'
    metrics_path = 'logs/metrics.json'
    
    if not os.path.exists(journal_path):
        print("Error: No trade journal found. Start the bot to generate data.")
        return

    with open(journal_path, 'r') as f:
        trades = json.load(f)
    
    df = pd.DataFrame(trades)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for closed trades (those with PnL)
    closed_trades = df[df['pnl'].notnull()].copy()
    
    if closed_trades.empty:
        print("No closed trades available for analysis yet.")
        return

    total_trades = len(closed_trades)
    wins = closed_trades[closed_trades['pnl'] > 0]
    losses = closed_trades[closed_trades['pnl'] <= 0]
    
    win_rate = (len(wins) / total_trades) * 100
    total_pnl = closed_trades['pnl'].sum()
    avg_win = wins['pnl'].mean() if not wins.empty else 0
    avg_loss = abs(losses['pnl'].mean()) if not losses.empty else 0
    profit_factor = (wins['pnl'].sum() / abs(losses['pnl'].sum())) if not losses.empty and losses['pnl'].sum() != 0 else float('inf')
    
    # Per-symbol breakdown
    symbol_stats = closed_trades.groupby('symbol')['pnl'].agg(['count', 'sum', 'mean']).rename(columns={'count': 'Trades', 'sum': 'Total PnL', 'mean': 'Avg PnL'})

    print("\n" + "="*50)
    print("BOT PERFORMANCE ANALYSIS REPORT")
    print("="*50)
    print(f"Total Closed Trades:  {total_trades}")
    print(f"Win Rate:             {win_rate:.1f}%")
    print(f"Net Profit/Loss:      ${total_pnl:.2f}")
    print(f"Profit Factor:        {profit_factor:.2f}")
    print(f"Average Win:          ${avg_win:.2f}")
    print(f"Average Loss:         ${avg_loss:.2f}")
    print("-" * 50)
    print("SYMBOL BREAKDOWN:")
    print(symbol_stats.to_string())
    print("-" * 50)
    
    # Load recent equity from metrics if available
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)
                if 'equity_history' in metrics and metrics['equity_history']:
                    history = metrics['equity_history']
                    # Handle both 'value' and 'equity' keys for compatibility
                    latest = history[-1]
                    latest_equity = latest.get('value', latest.get('equity', 0))
                    
                    initial = history[0]
                    initial_equity = initial.get('value', initial.get('equity', 100))
                    
                    if initial_equity > 0:
                        total_return = ((latest_equity / initial_equity) - 1) * 100
                        print(f"Current Equity:       ${latest_equity:.2f}")
                        print(f"Total Session Return: {total_return:+.2f}%")
        except Exception:
            pass
    
    print("="*50 + "\n")

if __name__ == "__main__":
    analyze_performance()
