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
    print(f"Using Yahoo Finance real-market candles at {args.interval} interval.")
    try:
        df = fetch_external_forex_data(symbol=args.symbol, interval=args.interval)
    except Exception as exc:
        print(f"Failed to fetch external data: {exc}")
        raise SystemExit(1)

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
