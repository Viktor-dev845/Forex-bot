import json
import os
from dotenv import load_dotenv

def load_config():
    """
    Loads configuration from config.json and overrides secrets 
    with environment variables.
    """
    # Load .env file
    load_dotenv()

    # Load base config from json
    if not os.path.exists('config.json'):
        raise FileNotFoundError("config.json not found in the current directory.")

    with open('config.json', 'r') as f:
        config = json.load(f)

    # Robust Override Logic
    def safe_set(keys, env_var):
        """Safely set a nested config value from env var if the path exists."""
        val = os.getenv(env_var)
        if not val:
            return
            
        curr = config
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                curr[key] = val
            else:
                if key not in curr:
                    return # Path doesn't exist
                curr = curr[key]

    # Alerts
    if 'alerts' in config:
        config['alerts']['smtp_password'] = os.getenv('SMTP_PASSWORD', config['alerts'].get('smtp_password', ''))

    # Brokers
    if 'brokers' in config:
        b = config['brokers']
        if 'alpaca' in b:
            b['alpaca']['api_key'] = os.getenv('ALPACA_API_KEY', b['alpaca'].get('api_key', ''))
            b['alpaca']['api_secret'] = os.getenv('ALPACA_API_SECRET', b['alpaca'].get('api_secret', ''))
        if 'oanda' in b:
            b['oanda']['account_id'] = os.getenv('OANDA_ACCOUNT_ID', b['oanda'].get('account_id', ''))
            b['oanda']['access_token'] = os.getenv('OANDA_ACCESS_TOKEN', b['oanda'].get('access_token', ''))
        if 'mt5' in b:
            b['mt5']['login'] = os.getenv('MT5_LOGIN', b['mt5'].get('login', ''))
            b['mt5']['password'] = os.getenv('MT5_PASSWORD', b['mt5'].get('password', ''))
        if 'deriv' in b:
            b['deriv']['api_token'] = os.getenv('DERIV_API_TOKEN', b['deriv'].get('api_token', ''))

    return config
