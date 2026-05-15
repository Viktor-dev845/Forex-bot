"""
Hardened LSTM-based Trading Model for Directional Classification.
Converts raw price sequences into Buy/Sell Probabilities.
"""

import torch
import torch.nn as nn
import numpy as np

class TradingLSTM(nn.Module):
    """
    An LSTM model for directional classification.
    """
    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2):
        super(TradingLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.LeakyReLU(0.01),
            nn.Dropout(dropout),
            nn.Linear(32, 1) # Probability Output
        )
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_output = lstm_out[:, -1, :]
        return self.fc(last_output) # Raw logits for BCEWithLogitsLoss during training

def create_classification_sequences(data, raw_prices, seq_length=30, horizon=5, threshold=0.001):
    """
    Hardened Sequence Creator: Looks for moves > 0.1% (Institutional Strength).
    """
    X, y = [], []
    
    for i in range(len(data) - seq_length - horizon):
        X.append(data[i:i + seq_length])
        
        current_price = raw_prices[i + seq_length - 1]
        future_price = raw_prices[i + seq_length + horizon - 1]
        
        # Binary: 1 if strong move up, 0 if flat or down
        if future_price > current_price * (1 + threshold):
            y.append(1)
        else:
            y.append(0)
            
    X_arr, y_arr = np.array(X), np.array(y)
    
    # Print class balance for debugging
    pos_pct = (sum(y_arr) / len(y_arr)) * 100
    print(f"Dataset Balance: {pos_pct:.1f}% UP signals | {100-pos_pct:.1f}% FLAT/DOWN signals")
    
    return X_arr, y_arr
