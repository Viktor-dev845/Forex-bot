"""
Training Pipeline for the LSTM Trading Model.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import argparse

from models.lstm_model import TradingLSTM, create_sequences
from feature_engine import FeatureEngine


def train_model(ticker="R_75", seq_length=30, epochs=100, batch_size=32, learning_rate=0.001):
    """
    Complete training pipeline with local data and fine-tuning.
    """
    print("=" * 50)
    print(f"LSTM Automated Retraining for {ticker}")
    print("=" * 50)
    
    # Step 1: Load Local Data
    print(f"\n[1/5] Loading local data for {ticker}...")
    file_path = f"data/raw/{ticker}.csv"
    if not os.path.exists(file_path):
        print(f"Error: Data file {file_path} not found.")
        return None
        
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    if len(df) < 250: # Increased requirement for feature generation
        print("Not enough data to train (min 250 rows required).")
        return None
        
    print(f"Loaded {len(df)} rows.")

    # Step 2: Preprocess using FeatureEngine
    print("\n[2/5] Preprocessing data with FeatureEngine...")
    try:
        feature_engine = FeatureEngine(ticker=ticker)
        
        # Generate features
        df_features = feature_engine.generate_features(df)
        
        # Check if we have enough data after feature generation (SMA(200) etc.)
        if len(df_features) < seq_length * 2:
            print(f"Not enough data remaining after feature generation ({len(df_features)} rows) to create sequences.")
            return None

        # Normalize the data and fit the scaler
        df_normalized = feature_engine.normalize_data(df_features, fit_scaler=True)
        
        # Define feature columns - all numeric columns from the normalized df
        feature_columns = [col for col in df_normalized.columns if df_normalized[col].dtype in [np.int64, np.float64]]
        data = df_normalized[feature_columns].values
        print(f"Processed data shape: {data.shape}")
        
    except Exception as e:
        print(f"Preprocessing error: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Step 3: Create Sequences
    print("\n[3/5] Creating sequences...")
    # Target is the 'Close' price, which we want to predict
    target_col_index = feature_columns.index('Close')
    X, y = create_sequences(data, seq_length=seq_length, target_col_index=target_col_index)
    
    if len(X) == 0:
        print("No sequences created. Check data length and sequence length.")
        return None
        
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    # Tensors
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.FloatTensor(y_train)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.FloatTensor(y_test)

    train_dataset = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    # Step 4: Initialize or Load Model
    print("\n[4/5] Initializing model...")
    input_size = X_train.shape[2]
    model = TradingLSTM(input_size=input_size, hidden_size=32, num_layers=2, output_size=1) # Output size is 1 (predicting 'Close')
    
    model_path = f"models/{ticker}_lstm.pth"
    if os.path.exists(model_path):
        try:
            print(f"Loading existing weights from {model_path} for fine-tuning...")
            checkpoint = torch.load(model_path)
            # Check if input size matches
            if checkpoint.get('input_size') == input_size:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                print("Input size mismatch (new features?), starting fresh.")
        except Exception as e:
            print(f"Error loading checkpoint: {e}. Starting fresh.")
    
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-2)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

    # Early Stopping params
    best_loss = float('inf')
    patience = 15
    patience_counter = 0
    best_model_state = None

    # Training Loop
    print(f"Training for {epochs} epochs...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            predictions = model(batch_X)
            loss = criterion(predictions, batch_y.float())
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        avg_train_loss = total_loss / len(train_loader)
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_preds = model(X_test_t)
            val_loss = criterion(val_preds, y_test_t.float()).item()
            
        scheduler.step(val_loss)
        
        if val_loss < best_loss:
            best_loss = val_loss
            patience_counter = 0
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
            
        if (epoch + 1) % 5 == 0:
            print(f"Epoch {epoch+1:03d} | Train Loss: {avg_train_loss:.4f} | Val Loss: {val_loss:.4f} | Patience: {patience_counter}/{patience}")
            
        if patience_counter >= patience:
            print(f"Early stopping triggered at epoch {epoch+1}")
            break

    # Step 5: Evaluate
    print("\n[5/5] Evaluating Best Model...")
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
        
    model.eval()
    with torch.no_grad():
        test_logits = model(X_test_t)
        test_probs = torch.sigmoid(test_logits)
        test_preds = (test_probs > 0.5).float()
        correct = (test_preds == y_test_t.float()).sum().item()
        accuracy = correct / len(y_test_t)
        
    print(f"Test Accuracy: {accuracy * 100:.2f}%")

    # Save
    torch.save({
        'model_state_dict': model.state_dict(),
        'input_size': input_size,
        'seq_length': seq_length,
        'ticker': ticker,
        'accuracy': accuracy,
        'feature_columns': feature_columns # Save feature columns
    }, model_path)
    print(f"Model saved to {model_path}")
    return accuracy

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str, default="R_75")
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()

    train_model(ticker=args.ticker, epochs=args.epochs)
