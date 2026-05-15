"""
Shared Enums and DataClasses for the AI Trading Bot.
Consolidated here to prevent circular dependencies.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class TradeAction(Enum):
    GO_LONG = auto()
    GO_SHORT = auto()
    CLOSE_POSITION = auto()
    DO_NOTHING = auto()

@dataclass
class TradeRecord:
    timestamp: str
    symbol: str
    side: str  # BUY, SELL, CLOSE
    quantity: float
    price: float
    order_id: str
    pnl: Optional[float] = None
    notes: str = ""

@dataclass
class ForexRiskParameters:
    """Configuration for forex-specific risk."""
    risk_per_trade_pct: float = 0.01   # Risk 1% of account per trade
    stop_loss_atr_multiplier: float = 1.5  # Stop loss distance in multiples of ATR
    risk_reward_ratio: float = 2.0

@dataclass
class RiskParameters:
    """Configuration for risk management."""
    risk_per_trade_pct: float = 0.01  # Risk 1% of account per trade (for non-forex)
    max_daily_loss_pct: float = 0.02
    stop_loss_pct: float = 0.02 # Used for calculating non-forex SL price
    take_profit_pct: float = 0.04 # Used for calculating non-forex TP price
    max_open_positions: int = 3
    min_confidence: float = 0.55
    trailing_stop_pct: float = 0.015  # Trailing stop distance (1.5%)
    trailing_activation_pct: float = 0.01  # Activate trailing after 1% profit
    forex_risk: Optional[ForexRiskParameters] = None
