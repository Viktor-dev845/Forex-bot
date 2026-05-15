"""
Institutional-Grade Training Pipeline for LSTM Classifier.
Includes Minority Oversampling, Early Stopping, and Precision Analysis.
"""

import sys
import os
import glob
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import argparse

from models.lstm_model import TradingLSTM, create_classification_sequences
from feature_engine import FeatureEngine

def load_and_merge_data(ticker):
    pattern = f"data/raw/{ticker}*.csv"
    files = glob.glob(pattern)
    if not files: return None
    print(f"Found {len(files)} data files for {ticker}. Merging...")
    df_list = []
    for f in files:
        try:
            temp_df = pd.read_csv(f, index_col=0, parse_dates=True)
            df_list.append(temp_df)
        except Exception: pass
    df = pd.concat(df_list)
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)
    return df

def analyze_precision(y_true, probs):
    thresholds = [0.5, 0.55, 0.6, 0.65]
    print("\n--- Institutional Precision Report ---")
    print(f"Max Conf Predicted: {probs.max():.2%}")
    print(f"{'Threshold':<12} | {'Trades':<10} | {'Win Rate':<10}")
    print("-" * 40)
    for t in thresholds:
        mask = (probs >= t)
        count = mask.sum()
        if count > 0:
            win_rate = (y_true[mask] == 1).mean()
            print(f"Conf > {t:.0%}  | {int(count):<10} | {win_rate:.2%}")
        else:
            print(f"Conf > {t:.0%}  | 0          | N/A")
    print("-" * 40)

def train_classification_model(ticker="R_75", seq_length=10, epochs=100):
    print(f"--- Institutional Hardening: {ticker} Training ---")
    df = load_and_merge_data(ticker)
    if df is None or len(df) < 500: return None
    
    # Spike-Specific Logic
    is_spike_index = "Boom" in ticker or "Crash" in ticker
    seq_length = 6 if is_spike_index else 30
    horizon = 1 if is_spike_index else 3
    threshold = 0.0004 if is_spike_index else 0.0008

    fe = FeatureEngine(ticker=ticker)
    df_features = fe.generate_features(df)
    df_norm = fe.normalize_data(df_features, fit_scaler=True)
    
    feature_cols = [col for col in df_norm.columns if df_norm[col].dtype in [np.int64, np.float64]]
    data = df_norm[feature_cols].values
    raw_prices = df_features['Close'].values
    
    X, y = create_classification_sequences(data, raw_prices, seq_length=seq_length, horizon=horizon, threshold=threshold)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, shuffle=False)
    
    # INSTITUTIONAL FIX: SMOTE-style Oversampling
    # If we have too few UP signals, the model will always predict 0. 
    # We duplicate the UP signals to reach a 40/60 balance.
    pos_idx = np.where(y_train == 1)[0]
    neg_idx = np.where(y_train == 0)[0]
    
    if len(pos_idx) > 0:
        multiplier = int(len(neg_idx) / len(pos_idx) * 0.8) # Target 40% pos
        if multiplier > 1:
            print(f"Oversampling UP signals {multiplier}x to fix class imbalance...")
            X_pos_repeated = np.repeat(X_train[pos_idx], multiplier, axis=0)
            y_pos_repeated = np.repeat(y_train[pos_idx], multiplier, axis=0)
            X_train = np.concatenate([X_train, X_pos_repeated])
            y_train = np.concatenate([y_train, y_pos_repeated])

    X_t = torch.FloatTensor(X_train)
    y_t = torch.FloatTensor(y_train).unsqueeze(1)
    X_val_t = torch.FloatTensor(X_test)
    y_val_t = torch.FloatTensor(y_test).unsqueeze(1)
    
    dataset = TensorDataset(X_t, y_t)
    loader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    model = TradingLSTM(input_size=X.shape[2], hidden_size=64, num_layers=2)
    criterion = nn.BCEWithLogitsLoss() # Weight is handled by oversampling
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0003, weight_decay=1e-4)
    
    best_loss = float('inf')
    patience = 15
    trigger_times = 0
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val_t)
            val_loss = criterion(val_outputs, y_val_t).item()
            
        if (epoch+1) % 5 == 0:
            print(f"Epoch {epoch+1:02d} | Val Loss: {val_loss:.4f}")
            
        if val_loss < best_loss:
            best_loss = val_loss
            trigger_times = 0
            torch.save(model.state_dict(), f"models/{ticker}_best_weights.pth")
        else:
            trigger_times += 1
            if trigger_times >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
                
    model.load_state_dict(torch.load(f"models/{ticker}_best_weights.pth"))
    model.eval()
    with torch.no_grad():
        logits = model(X_val_t)
        probs = torch.sigmoid(logits).squeeze().numpy()
        analyze_precision(y_test, probs)
        
    save_path = f"models/{ticker}_lstm.pth"
    torch.save({'model_state_dict': model.state_dict(), 'input_size': X.shape[2], 'accuracy': best_loss}, save_path)
    print(f"Balanced Model Saved: {save_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str, default="Volatility 75 Index")
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()
    train_classification_model(ticker=args.ticker, epochs=args.epochs)
