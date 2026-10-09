"""
Fetch Massive Clean Training Data via MetaTrader 5 (MT5).

MT5 is already connected and running — this is the most reliable way
to fetch historical data for Boom 1000 and Step Index.

Usage:
    python fetch_training_data.py
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 package not installed.")
    print("Run: pip install MetaTrader5")
    sys.exit(1)

# ─── Configuration ──────────────────────────────────────────────────────────
SYMBOLS = [
    "Boom 1000 Index",
    "Step Index",
]

TIMEFRAME = mt5.TIMEFRAME_H1   # 1-Hour candles
MAX_CANDLES = 5000              # Maximum candles to fetch per symbol
OUTPUT_DIR = "data/raw"
# ────────────────────────────────────────────────────────────────────────────


def fetch_symbol_mt5(symbol, timeframe, n_candles):
    """Fetch historical OHLCV candles for a symbol from MT5."""
    print(f"\n--- Fetching {symbol} ---")

    # Ensure symbol is available in MT5's market watch
    if not mt5.symbol_select(symbol, True):
        print(f"  [WARNING] Could not select {symbol} in Market Watch.")
        print(f"  Make sure '{symbol}' is added to your MT5 Market Watch panel.")
        return None

    # Fetch candles
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_candles)

    if rates is None or len(rates) == 0:
        err = mt5.last_error()
        print(f"  [ERROR] No data returned. MT5 Error: {err}")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df.set_index('time', inplace=True)
    df.index = df.index.tz_localize(None)  # Remove timezone for cleaner CSV

    df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'tick_volume': 'Volume'
    }, inplace=True)

    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    # ── Quality Checks ────────────────────────────────────────────────────
    initial_rows = len(df)
    df = df.dropna()
    df = df[(df['High'] >= df['Low'])]           # Valid OHLC
    df = df[(df['Close'] > 0) & (df['Open'] > 0)]  # No zero prices
    df = df[~df.index.duplicated(keep='first')]  # Remove duplicate timestamps
    df = df.sort_index()
    clean_rows = len(df)

    print(f"  Fetched:       {initial_rows} rows")
    print(f"  After cleaning:{clean_rows} rows")
    print(f"  Date range:    {df.index[0]} to {df.index[-1]}")
    print(f"  Price range:   {df['Close'].min():.4f} to {df['Close'].max():.4f}")

    # Class balance analysis (how many candles go down vs up)
    down_candles = (df['Close'] < df['Open']).sum()
    up_candles = (df['Close'] >= df['Open']).sum()
    print(f"  Class balance: {down_candles} DOWN ({down_candles/clean_rows*100:.1f}%) | "
          f"{up_candles} UP ({up_candles/clean_rows*100:.1f}%)")

    if clean_rows < 500:
        print(f"  [WARNING] Only {clean_rows} clean rows — may not be enough for robust training.")

    return df


def main():
    print("=" * 60)
    print("MT5 Massive Training Data Fetcher")
    print("=" * 60)
    print(f"Symbols:  {SYMBOLS}")
    print(f"Candles:  {MAX_CANDLES} per symbol (1-Hour timeframe)")
    print(f"Output:   {OUTPUT_DIR}/")
    print("=" * 60)

    # ── Initialize MT5 ────────────────────────────────────────────────────
    if not mt5.initialize():
        print(f"\n[ERROR] Could not connect to MT5: {mt5.last_error()}")
        print("Make sure your MT5 terminal is open and running.")
        sys.exit(1)

    terminal_info = mt5.terminal_info()
    print(f"\n[OK] Connected to MT5: {terminal_info.name}")
    account_info = mt5.account_info()
    if account_info:
        print(f"[OK] Account: {account_info.login} | Balance: ${account_info.balance:.2f}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = {}

    try:
        for symbol in SYMBOLS:
            df = fetch_symbol_mt5(symbol, TIMEFRAME, MAX_CANDLES)

            if df is not None and len(df) > 0:
                filepath = os.path.join(OUTPUT_DIR, f"{symbol}.csv")
                df.to_csv(filepath)
                print(f"  [SAVED] {filepath}")
                results[symbol] = {"rows": len(df), "path": filepath, "status": "OK"}
            else:
                results[symbol] = {"rows": 0, "path": None, "status": "FAILED"}

    finally:
        mt5.shutdown()
        print("\nMT5 connection closed.")

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FETCH SUMMARY")
    print("=" * 60)
    all_ok = True
    for name, info in results.items():
        if info["status"] == "OK":
            print(f"  OK  {name}: {info['rows']} rows saved to {info['path']}")
        else:
            print(f"  FAIL {name}: Data fetch failed")
            all_ok = False

    if all_ok:
        print("\nAll data fetched successfully!")
        print("Next step: run the training script:")
        print('  python train.py --ticker "Boom 1000 Index" --epochs 100')
        print('  python train.py --ticker "Step Index" --epochs 100')
    else:
        print("\nSome symbols failed. Check that they are visible in your MT5 Market Watch.")


if __name__ == "__main__":
    main()
