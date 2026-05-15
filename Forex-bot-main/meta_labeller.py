import pandas as pd
import numpy as np
import xgboost as xgb
import os
import joblib
from typing import Dict, List, Tuple
import logging

class MetaLabeller:
    """
    Meta-Labeling System (Marcos López de Prado).
    A secondary model that predicts the probability of a primary signal being correct.
    """
    def __init__(self, ticker: str, model_dir: str = "models"):
        self.ticker = ticker
        self.model_path = os.path.join(model_dir, f"{ticker}_meta_model.joblib")
        self.model = None
        self.logger = logging.getLogger(__name__)

    def create_labels(self, df: pd.DataFrame, signals: pd.Series, pt: float = 2.0, sl: float = 1.0) -> pd.DataFrame:
        """
        Generates meta-labels based on Triple Barrier Method (Simplified).
        signals: 1 for Long, -1 for Short, 0 for Nothing
        pt: Profit Taking multiplier
        sl: Stop Loss multiplier
        """
        df = df.copy()
        df['target'] = 0 # Default: Loss
        
        # Calculate daily volatility (rolling std)
        df['vol'] = df['Close'].pct_change().rolling(window=100).std()
        
        for i in range(len(df) - 50): # Look ahead 50 candles
            if signals.iloc[i] == 0: continue
            
            entry_price = df['Close'].iloc[i]
            vol = df['vol'].iloc[i]
            
            # Barriers
            upper_barrier = entry_price * (1 + vol * pt) if signals.iloc[i] == 1 else entry_price * (1 + vol * sl)
            lower_barrier = entry_price * (1 - vol * sl) if signals.iloc[i] == 1 else entry_price * (1 - vol * pt)
            
            # Check which barrier is hit first
            for j in range(1, 50):
                current_price = df['Close'].iloc[i + j]
                
                if signals.iloc[i] == 1: # Long
                    if current_price >= upper_barrier:
                        df.at[df.index[i], 'target'] = 1
                        break
                    elif current_price <= lower_barrier:
                        break
                elif signals.iloc[i] == -1: # Short
                    if current_price <= lower_barrier:
                        df.at[df.index[i], 'target'] = 1
                        break
                    elif current_price >= upper_barrier:
                        break
                        
        return df

    def train(self, X: pd.DataFrame, y: pd.Series):
        """Trains the secondary meta-model (XGBoost Classifier)."""
        self.logger.info(f"Training Meta-Model for {self.ticker} with {len(X)} samples...")
        
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            objective='binary:logistic',
            random_state=42
        )
        
        self.model.fit(X, y)
        joblib.dump(self.model, self.model_path)
        self.logger.info(f"Meta-Model saved to {self.model_path}")

    def predict_probability(self, features: Dict) -> float:
        """Returns the probability that the primary signal is correct."""
        if self.model is None:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                return 1.0 # Default to pass if no meta-model exists
                
        # Convert features to DMatrix or DF
        X = pd.DataFrame([features])
        prob = self.model.predict_proba(X)[0][1]
        return float(prob)

    def should_execute(self, ensemble_signal: str, features: Dict, threshold: float = 0.5) -> bool:
        """Final decision: Should the bot execute this signal?"""
        if ensemble_signal == 'NEUTRAL': return False
        
        prob = self.predict_probability(features)
        self.logger.info(f"Meta-Confidence for {ensemble_signal}: {prob:.2%}")
        
        return prob >= threshold
