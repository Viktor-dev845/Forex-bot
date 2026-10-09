import torch
import torch.nn as nn
import math

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)

    def forward(self, x):
        return x + self.pe[:x.size(0), :]

class TradingTransformer(nn.Module):
    def __init__(self, input_size, d_model=64, nhead=4, num_layers=2, output_size=1, dropout=0.1):
        super(TradingTransformer, self).__init__()
        self.model_type = 'Transformer'
        self.src_mask = None
        self.pos_encoder = PositionalEncoding(d_model)
        self.encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dropout=dropout)
        self.transformer_encoder = nn.TransformerEncoder(self.encoder_layer, num_layers=num_layers)
        self.encoder = nn.Linear(input_size, d_model)
        self.d_model = d_model
        self.decoder = nn.Linear(d_model, output_size)

    def forward(self, src):
        # src shape: (batch_size, seq_len, input_size)
        src = src.transpose(0, 1) # (seq_len, batch_size, input_size)
        src = self.encoder(src) * math.sqrt(self.d_model)
        src = self.pos_encoder(src)
        output = self.transformer_encoder(src)
        # Take the last sequence output
        output = output[-1, :, :]
        output = self.decoder(output)
        return output  # Raw logits — sigmoid applied by loss function or at inference

