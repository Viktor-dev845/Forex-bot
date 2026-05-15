import pandas as pd
import numpy as np
import os
from strategy_engine import EnsembleStrategy, TradeAction
from meta_labeller import MetaLabeller
from feature_engine import FeatureEngine
import logging

# Setup minimal logging for backtest
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Backtest")

def run_backtest(ticker: str, initial_capital: float = 1000):
    logger.info(f"\n{'='*20} Backtesting {ticker} {'='*20}")
    
    # 1. Load Data
    data_path = f"data/raw/{ticker}.csv"
    if not os.path.exists(data_path):
        logger.error(f"Data for {ticker} not found.")
        return
    
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)
    fe = FeatureEngine()
    df = fe.generate_features(df)
    
    # 2. Setup Strategy
    config = {
        'risk': {'min_confidence': 0.55},
        'model': {'strategy': 'ensemble'}
    }
    strategy = EnsembleStrategy(config)
    meta = MetaLabeller(ticker)
    
    # 3. Simulate Loop
    equity = initial_capital
    position = None
    trades = 0
    wins = 0
    conflicts_blocked = 0
    meta_blocked = 0
    
    # Simulate walk-forward (last 200 candles)
    for i in range(len(df) - 200, len(df)):
        # Mock predictions (simulating LSTM/XGBoost)
        # In a real backtest we'd load models, but here we're testing the filters
        # We'll generate mock predictions with varying spread to test conflict logic
        p1 = np.random.uniform(0.4, 0.9)
        p2 = np.random.uniform(0.4, 0.9) if p1 > 0.5 else np.random.uniform(0.1, 0.6)
        
        preds = {'lstm': p1, 'xgboost': p2}
        
        # Test Ensemble Logic
        final_pred = strategy.get_weighted_prediction(preds)
        
        if final_pred == 0.5:
            conflicts_blocked += 1
            continue
            
        # Test Meta Logic
        features = df.iloc[i].to_dict()
        action = strategy.get_decision(preds, position)
        
        if action != TradeAction.DO_NOTHING:
            if not meta.should_execute(action.name, features):
                meta_blocked += 1
                continue
            
            # Simulate Trade Outcome
            trades += 1
            outcome = np.random.choice([1, 0], p=[0.55, 0.45]) # Basic win rate for sim
            if outcome == 1:
                wins += 1
                equity += equity * 0.02
            else:
                equity -= equity * 0.01
                
    logger.info(f"--- Results for {ticker} ---")
    logger.info(f"Initial: ${initial_capital} -> Final: ${equity:.2f}")
    logger.info(f"Total Trades: {trades}")
    logger.info(f"Win Rate: {(wins/trades*100 if trades > 0 else 0):.1f}%")
    logger.info(f"Conflict Penalty Blocks: {conflicts_blocked}")
    logger.info(f"Meta-Filter Blocks: {meta_blocked}")
    logger.info(f"{'='*50}")

if __name__ == "__main__":
    for ticker in ["Volatility 75 Index", "Crash 500 Index", "Boom 1000 Index"]:
        run_backtest(ticker)
