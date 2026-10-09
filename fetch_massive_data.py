import asyncio
from data_loader import fetch_external_forex_data
import os
import argparse

async def main():
    parser = argparse.ArgumentParser(description='Fetch independent real-market data for model training.')
    parser.add_argument('--symbol', type=str, default='EURUSD', help='Symbol to fetch data for')
    parser.add_argument('--interval', type=str, default='5m', help='External data interval matching live trading')
    args = parser.parse_args()
    
    print(f"Initializing external historical data collection for {args.symbol}...")
    
    df = None
    is_synthetic = any(x in args.symbol.upper() for x in ["VOLATILITY", "CRASH", "BOOM", "INDEX", "STEP"])
    
    if is_synthetic:
        print(f"Symbol {args.symbol} is a Synthetic Index. Bypassing Yahoo Finance and pulling directly from MT5...")
        from utils.data_loader import fetch_data_mt5
        data_map = fetch_data_mt5([args.symbol], n_candles=2000, timeframe="M5")
        if data_map and args.symbol in data_map:
            df = data_map[args.symbol]
    else:
        print(f"Using Yahoo Finance real-market candles at {args.interval} interval.")
        try:
            df = fetch_external_forex_data(symbol=args.symbol, interval=args.interval)
        except Exception as exc:
            print(f"Failed to fetch external data from Yahoo: {exc}")
            print(f"Falling back to MT5 for {args.symbol}...")
            from utils.data_loader import fetch_data_mt5
            data_map = fetch_data_mt5([args.symbol], n_candles=2000, timeframe="M5")
            if data_map and args.symbol in data_map:
                df = data_map[args.symbol]

    if df is not None and not df.empty:
        print(f"Successfully collected {len(df)} candles.")
        if not os.path.exists('data/raw'):
            os.makedirs('data/raw')
        
        path = f"data/raw/{args.symbol}.csv"
        df.to_csv(path)
        print(f"Data saved to {path}. Ready for AI training!")
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    asyncio.run(main())
