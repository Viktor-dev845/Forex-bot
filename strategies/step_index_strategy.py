"""
Step Index Strategy — Mean Reversion + Trend Confirmation

Step Index moves in fixed increments (steps of 0.1), making it:
  - Immune to slippage and teleporting spikes
  - Highly responsive to RSI mean reversion signals
  - Ideal for tight, reliable Stop Loss execution

Strategy Logic:
  Entry (SELL):  RSI was oversold (<30) and recovers above 35 + price below BB Middle
  Entry (BUY):   RSI was overbought (>70) and falls below 65 + price above BB Middle
  Exit:          Fixed TP of 15 pts OR SL of 10 pts (Stop Losses work here unlike Boom!)
  ML Overlay:    Only execute if ML ensemble confidence >= 60%
"""

import numpy as np


class StepIndexStrategy:
    """
    Dedicated Mean Reversion strategy for Step Index.
    Fully separate from the Boom 1000 Spike Sniper.
    """

    def __init__(self, config=None, logger=None):
        self.config = config or {}
        self.logger = logger

        # RSI thresholds
        self.rsi_oversold = 30.0
        self.rsi_overbought = 70.0
        self.rsi_recover_from_oversold = 35.0   # RSI must cross back above this after being oversold
        self.rsi_recover_from_overbought = 65.0  # RSI must cross back below this after being overbought

        # Risk per trade (Step Index SL actually works — no slippage)
        self.take_profit_pts = 15.0   # 15 points TP
        self.stop_loss_pts = 10.0     # 10 points SL (strict — slippage-free on Step Index)

        # ML confidence gate
        self.min_ml_confidence = 0.60

        # State tracking per call
        self._was_oversold = False
        self._was_overbought = False

    def log(self, msg, level="info"):
        if self.logger:
            if level == "warning":
                self.logger.warning(f"[Step Index Strategy] {msg}")
            else:
                self.logger.info(f"[Step Index Strategy] {msg}")

    def analyze(self, current_rsi, current_price, bb_middle, bb_upper, bb_lower, ml_confidence=0.5):
        """
        Analyze current market state and return a trade signal.

        Args:
            current_rsi (float): Current 14-period RSI value
            current_price (float): Current close price
            bb_middle (float): Bollinger Band middle line (20 SMA)
            bb_upper (float): Bollinger Band upper band
            bb_lower (float): Bollinger Band lower band
            ml_confidence (float): Ensemble model confidence (0.0 - 1.0)

        Returns:
            str: 'BUY', 'SELL', or 'WAIT'
        """
        signal = "WAIT"

        # --- Track Oversold / Overbought State ---
        if current_rsi < self.rsi_oversold:
            self._was_oversold = True
            self._was_overbought = False
        elif current_rsi > self.rsi_overbought:
            self._was_overbought = True
            self._was_oversold = False

        # --- SELL Signal: RSI recovering from overbought ---
        # Price was overbought and is now pulling back (reverting to mean)
        if self._was_overbought and current_rsi <= self.rsi_recover_from_overbought:
            if current_price >= bb_middle:  # Price still above middle — room to drop
                if ml_confidence >= self.min_ml_confidence:
                    signal = "SELL"
                    self._was_overbought = False  # Reset state after firing
                    self.log(f"SELL signal. RSI={current_rsi:.1f} recovering from overbought. "
                             f"Price={current_price:.2f} above BB Mid={bb_middle:.2f}. "
                             f"ML Conf={ml_confidence:.2f}")
                else:
                    self.log(f"SELL blocked — ML confidence too low ({ml_confidence:.2f} < {self.min_ml_confidence}). "
                             f"RSI={current_rsi:.1f}")

        # --- BUY Signal: RSI recovering from oversold ---
        # Price was oversold and is now bouncing (reverting to mean)
        elif self._was_oversold and current_rsi >= self.rsi_recover_from_oversold:
            if current_price <= bb_middle:  # Price still below middle — room to rise
                if ml_confidence >= self.min_ml_confidence:
                    signal = "BUY"
                    self._was_oversold = False  # Reset state after firing
                    self.log(f"BUY signal. RSI={current_rsi:.1f} recovering from oversold. "
                             f"Price={current_price:.2f} below BB Mid={bb_middle:.2f}. "
                             f"ML Conf={ml_confidence:.2f}")
                else:
                    self.log(f"BUY blocked — ML confidence too low ({ml_confidence:.2f} < {self.min_ml_confidence}). "
                             f"RSI={current_rsi:.1f}")
        else:
            self.log(f"WAIT. RSI={current_rsi:.1f}. "
                     f"Was Oversold={self._was_oversold}, Was Overbought={self._was_overbought}.")

        return signal

    def get_exit_levels(self, entry_price, direction):
        """
        Calculate Stop Loss and Take Profit for a Step Index trade.

        Because Step Index has zero slippage, these levels are respected exactly.

        Args:
            entry_price (float): The price the trade was opened at
            direction (str): 'BUY' or 'SELL'

        Returns:
            tuple: (take_profit_price, stop_loss_price)
        """
        if direction == "BUY":
            tp = entry_price + self.take_profit_pts
            sl = entry_price - self.stop_loss_pts
        else:  # SELL
            tp = entry_price - self.take_profit_pts
            sl = entry_price + self.stop_loss_pts

        self.log(f"Exit levels for {direction} @ {entry_price:.2f}: TP={tp:.2f}, SL={sl:.2f}")
        return tp, sl
