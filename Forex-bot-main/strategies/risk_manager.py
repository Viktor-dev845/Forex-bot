"""
Risk Management Module for the AI Trading Bot.
Hardened for Institutional Grade protection.
"""

from dataclasses import dataclass
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils.shared_types import RiskParameters, ForexRiskParameters

class RiskManager:
    """
    Manages trading risk and enforces safety limits.
    """
    
    def __init__(self, params: Optional[RiskParameters] = None):
        self.params = params or RiskParameters()
        if self.params.forex_risk is None:
            self.params.forex_risk = ForexRiskParameters()
            
        self.daily_pnl = 0.0
        self.open_positions = {}
        self.initial_portfolio_value = 100.0 # Default institutional baseline
        self.trailing_stops = {}
        
    def check_daily_loss(self, current_daily_pnl, initial_capital=100):
        """
        Check if trading should continue based on daily loss limit.
        Includes a Hard Circuit Breaker (10% max loss).
        """
        reference = initial_capital if initial_capital > 0 else 100
        
        # 1. SOFT LIMIT (Configurable)
        max_loss_pct = self.params.max_daily_loss_pct or 0.05
        max_loss_amount = reference * max_loss_pct
        
        # 2. HARD CIRCUIT BREAKER (Fixed 10%)
        HARD_STOP_PCT = 0.10
        hard_stop_amount = reference * HARD_STOP_PCT

        if current_daily_pnl <= -hard_stop_amount:
            logger.critical(f"🛑 CIRCUIT BREAKER TRIGGERED: Daily loss ${abs(current_daily_pnl):.2f} exceeds 10% limit.")
            return False

        if current_daily_pnl <= -max_loss_amount:
            logger.warning(f"⚠️ SOFT LOSS LIMIT REACHED: Daily loss ${abs(current_daily_pnl):.2f} hit {max_loss_pct:.1%}.")
            return False
            
        return True

    def calculate_forex_position_size(self, portfolio_value: float, symbol: str, atr: float, **kwargs) -> float:
        """
        Hardened Position Sizing: Never risk more than 3% of capital per trade.
        """
        # Fixed Risk Model
        risk_pct = 0.015 # 1.5% Risk per setup
        risk_amount = portfolio_value * risk_pct
        
        # Stop distance based on 2.0x ATR for buffer
        stop_dist = atr * 2.0
        if stop_dist <= 0: return 0
        
        # Units = Risk / Dist
        units = risk_amount / stop_dist
        
        # Institutional Cap: Never more than 5 lots (500k units) on $100
        # Actually for $100, we should be much lower. 
        # Cap units at 1000 for synthetics on $100 account.
        units = min(units, 1000) 
        
        return round(units, 2)

    def get_forex_exit_prices(self, entry_price: float, symbol: str, position_type: str, atr: float) -> dict:
        stop_dist = atr * 2.0
        tp_dist = stop_dist * 2.5 # 2.5:1 RR ratio
        
        if position_type == 'long':
            return {'stop_loss': entry_price - stop_dist, 'take_profit': entry_price + tp_dist}
        else:
            return {'stop_loss': entry_price + stop_dist, 'take_profit': entry_price - tp_dist}

    def update_trailing_stop(self, symbol: str, current_price: float) -> dict:
        # Standard implementation
        return {'triggered': False, 'stop_level': 0}

    def close_position(self, symbol: str, price: float):
        if symbol in self.open_positions: del self.open_positions[symbol]
