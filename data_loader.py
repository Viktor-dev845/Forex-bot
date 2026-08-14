"""
Data Loader for Deriv API

This script fetches historical candle data for synthetic indices from Deriv's platform.
"""
import asyncio
from deriv_api import DerivAPI
import pandas as pd

from utils.config_loader import load_config

async def fetch_historical_data(symbol="R_75", time_interval="1h", max_candles=5000):
    """
    Fetches historical candle data from the Deriv API.

    Args:
        symbol (str): The symbol for the synthetic index (e.g., "R_75").
        time_interval (str): The data interval (e.g., "1h", "1d").
        max_candles (int): The maximum number of candles to fetch.

    Returns:
        pandas.DataFrame: A DataFrame containing OHLCV data, indexed by datetime.
                          Returns None if fetching fails.
    """
    print(f"Fetching historical data for {symbol} ({time_interval})...")

    # Load API token from config
    config = load_config()
    api_token = config.get('brokers', {}).get('deriv', {}).get('api_token')
    if not api_token or api_token == 'YOUR_DERIV_API_TOKEN':
        print("Error: Deriv API token not found or not set in environment variables.")
        return None

    # Map our interval to Deriv's granularity in seconds
    granularity_map = {
        "1m": 60,
        "2m": 120,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400
    }
    granularity = granularity_map.get(time_interval)
    if not granularity:
        print(f"Error: Invalid time interval '{time_interval}'.")
        return None

    # Use user's custom app_id
    working_app_ids = ["344Jxh9ST3khy7uu8Z3Ic"]
    
    connected = False
    for app_id in working_app_ids:
        try:
            print(f"Trying app_id: {app_id}...")
            api = DerivAPI(app_id=app_id)
            await api.authorize(api_token)
            print(f"[OK] Successfully authenticated with app_id {app_id}")
            connected = True
            break
        except Exception as e:
            print(f"app_id {app_id} failed: {e}")
            if api:
                try:
                    await api.disconnect()
                except:
                    pass
            continue
    
    if not connected:
        print("[ERROR] All app_ids failed. Your API token may be invalid or expired.")
        print(f"Token (first 10 chars): {api_token[:10]}...")
        print("Please verify your token at: https://app.deriv.com/account/api-token")
        return None
    
    try:

        # Request historical data
        response = await api.ticks_history({
            'ticks_history': symbol,
            'style': 'candles',
            'end': 'latest',
            'count': max_candles,
            'granularity': granularity
        })

        if response.get('error'):
            print(f"Deriv API Error: {response['error'].get('message')}")
            return None

        candles = response.get('candles')
        if not candles:
            print("No candle data returned from API.")
            return None

        # Convert to pandas DataFrame
        df = pd.DataFrame(candles)
        df['Date'] = pd.to_datetime(df['epoch'], unit='s')
        df.set_index('Date', inplace=True)

        # Rename columns to standard format
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close'
        }, inplace=True)
        
        # Synthetics don't have real "exchange volume", but Deriv provides 'tick_count'
        # unmapped in the initial dataframe. We should check for it.
        if 'tick_count' in df.columns:
             df.rename(columns={'tick_count': 'Volume'}, inplace=True)
        elif 'Volume' not in df.columns:
             df['Volume'] = 1  # Default to 1 to avoid division by zero errors, not 1000 which distorts scales

        # Ensure correct column order and drop 'epoch'
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

        print(f"Successfully fetched {len(df)} candles.")
        print(df.tail())
        return df

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    finally:
        await api.disconnect()
        print("Disconnected from Deriv API.")


async def fetch_iqoption_data(symbol="EURUSD-OTC", time_interval="5m", max_candles=1000):
    """
    Fetches historical candle data from IQ Option.
    """
    try:
        from iqoptionapi.stable_api import IQ_Option
    except ImportError:
        print("Error: iqoptionapi not installed. pip install iqoptionapi")
        return None
        
    config = load_config()
    iq_config = config.get('brokers', {}).get('iqoption', {})
    email = iq_config.get('email')
    password = iq_config.get('password')
    
    if not email or not password or email == 'YOUR_IQOPTION_EMAIL':
        print("Error: IQ Option credentials not configured in config.json.")
        return None
        
    api = IQ_Option(email, password)
    status, reason = api.connect()
    
    if not status:
        print(f"IQ Option Connection failed: {reason}")
        return None
        
    print(f"Fetching IQ Option historical data for {symbol} ({time_interval})...")
    
    granularity_map = {
        "1m": 60,
        "2m": 120,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400
    }
    interval = granularity_map.get(time_interval, 300)
    
    import time
    end_from_time = time.time()
    
    all_candles = []
    candles_to_fetch = max_candles
    
    while candles_to_fetch > 0:
        chunk_size = min(candles_to_fetch, 1000)
        chunk = api.get_candles(symbol, interval, chunk_size, end_from_time)
        if not chunk:
            break
            
        all_candles.extend(chunk)
        
        earliest_time = chunk[0]['from']
        end_from_time = earliest_time - 1
        
        candles_to_fetch -= len(chunk)
        time.sleep(0.5) # Rate limit protection
    
    if not all_candles:
        print("No candle data returned from IQ Option API.")
        return None
        
    df = pd.DataFrame(all_candles)
    df.drop_duplicates(subset=['from'], inplace=True)
    df.sort_values('from', inplace=True)
    
    # IQ Option columns: 'id', 'from', 'to', 'open', 'close', 'min', 'max', 'volume'
    if 'from' in df.columns:
        df['Date'] = pd.to_datetime(df['from'], unit='s')
        df.set_index('Date', inplace=True)
        df.rename(columns={
            'open': 'Open',
            'max': 'High',
            'min': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        print(f"Successfully fetched {len(df)} candles from IQ Option.")
        return df
    else:
        print("Unexpected candle format from IQ Option.")
        return None

async def async_main():
    """Asynchronous main function to test the data loader."""
    config = load_config()
    
    market_type = config.get('bot', {}).get('market_type')
    if market_type == 'synthetics':
        symbols = config.get('markets', {}).get('synthetics', {}).get('symbols', [])
        if symbols:
            await fetch_historical_data(symbol=symbols[0])
    elif market_type == 'iqoption':
        symbols = config.get('markets', {}).get('iqoption', {}).get('symbols', [])
        if symbols:
            await fetch_iqoption_data(symbol=symbols[0])
    else:
        print(f"Market type is set to '{market_type}', unsupported by simple test script.")


def main():
    """Main function to test the data loader."""
    try:
        asyncio.run(async_main())
    except Exception as e:
        print(f"An error occurred in main: {e}")


if __name__ == "__main__":
    main()