import asyncio
from data_loader import fetch_iqoption_data
import os
import argparse

async def main():
    parser = argparse.ArgumentParser(description='Fetch historical data from IQ Option.')
    parser.add_argument('--symbol', type=str, default='NZDUSD-OTC', help='Symbol to fetch data for')
    args = parser.parse_args()
    
    print(f"Initializing massive historical data collection for {args.symbol}...")
    # Fetch 50,000 candles for robust training
    df = await fetch_iqoption_data(symbol=args.symbol, time_interval="2m", max_candles=50000)
    
    if df is not None:
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
