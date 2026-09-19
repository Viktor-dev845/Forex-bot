from enum import Enum, auto

class TradeAction(Enum):
    DO_NOTHING = auto()
    GO_LONG = auto()
    GO_SHORT = auto()
    CLOSE_POSITION = auto()

class BaseStrategy:
    def __init__(self, config: dict):
        self.config = config
        self.trading_hours_cfg = config.get('bot', {}).get('trading_hours', {})

    def _is_within_trading_hours(self) -> bool:
        if not self.trading_hours_cfg.get('enabled', False):
            return True
            
        import datetime
        now = datetime.datetime.now().time()
        start_str = self.trading_hours_cfg.get('start', '00:00')
        end_str = self.trading_hours_cfg.get('end', '23:59')
        
        try:
            start_time = datetime.datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.datetime.strptime(end_str, '%H:%M').time()
            
            if start_time <= end_time:
                return start_time <= now <= end_time
            else: # spans midnight
                return now >= start_time or now <= end_time
        except ValueError:
            return True # fallback if format is bad

    def get_decision(self, prediction: float, position_info: dict, symbol: str = None) -> TradeAction:
        """
        Based on a prediction and current position, return a trade action.
        """
        raise NotImplementedError("Should implement get_decision()")

class AIStrategy(BaseStrategy):
    def __init__(self, config: dict):
        super().__init__(config)
        risk_config = self.config.get('risk', {})
        self.long_entry_threshold = risk_config.get('min_confidence', 0.55)
        self.short_entry_threshold = 1 - self.long_entry_threshold
        # Using a neutral 0.5 as the exit threshold
        self.long_exit_threshold = 0.5
        self.short_exit_threshold = 0.5

    def get_decision(self, prediction: float, position_info: dict, symbol: str = None, trend_context: str = None) -> TradeAction:
        has_position = position_info is not None
        
        if has_position:
            pos_side = position_info['side']
            if pos_side == 'long' and prediction < self.long_exit_threshold:
                return TradeAction.CLOSE_POSITION
            elif pos_side == 'short' and prediction > self.short_exit_threshold:
                return TradeAction.CLOSE_POSITION
        else: # No position
            if not self._is_within_trading_hours():
                return TradeAction.DO_NOTHING

            if prediction > self.long_entry_threshold:
                action = TradeAction.GO_LONG
            elif prediction < self.short_entry_threshold:
                action = TradeAction.GO_SHORT
            else:
                return TradeAction.DO_NOTHING
            
            # Apply Safety Filter
            if symbol:
                sym_upper = symbol.upper()
            # Apply Smart Trend Filter (Confidence Scaling)
            # Instead of a blind block, we require massive confidence (>75%) to trade against the trend!
            if trend_context:
                if trend_context == 'UP' and action == TradeAction.GO_SHORT:
                    if prediction > 0.25: # Needs to be VERY strongly predicting DOWN (< 0.25)
                        logging.getLogger(__name__).warning(f"Blocked weak counter-trend SHORT trade on {symbol} (Conf={1-prediction:.0%}). Waiting for stronger overbought signal.")
                        return TradeAction.DO_NOTHING
                    else:
                        logging.getLogger(__name__).info(f"Allowed EXTREME overbought counter-trend SHORT on {symbol} (Conf={1-prediction:.0%})")
                
                if trend_context == 'DOWN' and action == TradeAction.GO_LONG:
                    if prediction < 0.75: # Needs to be VERY strongly predicting UP (> 0.75)
                        logging.getLogger(__name__).warning(f"Blocked weak counter-trend LONG trade on {symbol} (Conf={prediction:.0%}). Waiting for stronger oversold signal.")
                        return TradeAction.DO_NOTHING
                    else:
                        logging.getLogger(__name__).info(f"Allowed EXTREME oversold counter-trend LONG on {symbol} (Conf={prediction:.0%})")
            
            return action
        
        return TradeAction.DO_NOTHING

import logging

# ... (existing code)

class EnsembleStrategy(AIStrategy):
    """
    Weighted Ensemble Strategy: Uses accuracy-weighted voting instead of unanimous agreement.
    
    Entry: weighted_average >= threshold
    Exit: ANY model signals exit (risk-averse)
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        # Default equal weights. These can be updated by the bot based on model performance.
        self.model_weights = {'xgboost': 0.5, 'lstm': 0.5}
        ensemble_config = config.get('model', {}).get('ensemble', {})
        self.min_model_confidence = ensemble_config.get('min_model_confidence', 0.52)
        self.require_model_agreement = ensemble_config.get('require_model_agreement', True)
        self.counter_trend_confidence = ensemble_config.get('counter_trend_confidence', 0.60)
        self.logger = logging.getLogger(__name__) # Add logger
        
    def set_weights(self, weights: dict):
        """Update model weights based on recent accuracy. Weights should sum to 1."""
        total = sum(weights.values())
        if total > 0:
            self.model_weights = {k: v/total for k, v in weights.items()}  # Normalize
        
    def get_weighted_prediction(self, predictions: dict) -> float:
        """Calculate weighted average of model predictions."""
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for model_name, pred in predictions.items():
            # Skip failed predictions (None)
            if pred is None:
                self.logger.warning(f"Model '{model_name}' returned None (skipping from ensemble)")
                continue
                
            # Skip neutral predictions (0.5) - likely indicates failure
            if pred == 0.5:
                self.logger.warning(f"Model '{model_name}' returned neutral 0.5 (skipping from ensemble)")
                continue
            
            weight = self.model_weights.get(model_name, 0.5)
            weighted_sum += pred * weight
            weight_sum += weight
            
        if weight_sum > 0:
            final_pred = weighted_sum / weight_sum
            self.logger.info(f"Weighted prediction: {final_pred:.2%} (from {len(predictions)} models)")
            return final_pred
        else:
            self.logger.error("No valid model predictions available, returning neutral 0.5")
            return 0.5
        
    def get_decision(self, predictions: dict, position_info: dict, symbol: str = None, trend_context: str = None) -> TradeAction:
        has_position = position_info is not None
        
        # Calculate weighted ensemble prediction
        weighted_pred = self.get_weighted_prediction(predictions)
        
        # Check for exit first (still risk-averse: ANY model signals exit)
        if has_position:
            pos_side = position_info['side']
            
            # Exit if ANY model signals or weighted average crosses threshold
            if pos_side == 'long':
                if weighted_pred < self.long_exit_threshold or any(p < self.long_exit_threshold for p in predictions.values()):
                    return TradeAction.CLOSE_POSITION
            elif pos_side == 'short':
                if weighted_pred > self.short_exit_threshold or any(p > self.short_exit_threshold for p in predictions.values()):
                    return TradeAction.CLOSE_POSITION
        
        # If no position, check for entry using WEIGHTED AVERAGE (not all-agree)
        else:
            if not self._is_within_trading_hours():
                return TradeAction.DO_NOTHING
                
            long_threshold = self.long_entry_threshold
            short_threshold = self.short_entry_threshold
            if trend_context == 'DOWN':
                long_threshold = self.counter_trend_confidence
            elif trend_context == 'UP':
                short_threshold = 1 - self.counter_trend_confidence

            action = TradeAction.DO_NOTHING
            if weighted_pred > long_threshold:
                action = TradeAction.GO_LONG
            elif weighted_pred < short_threshold:
                action = TradeAction.GO_SHORT
            else:
                self.logger.info(
                    f"Signal skipped for {symbol}: weighted prediction {weighted_pred:.2%} "
                    f"is inside the active range ({short_threshold:.2%}-{long_threshold:.2%})"
                )
                return TradeAction.DO_NOTHING

            valid_predictions = [prediction for prediction in predictions.values() if prediction is not None and prediction != 0.5]
            if len(valid_predictions) < 2:
                self.logger.info(f"Signal skipped for {symbol}: ensemble requires both model predictions")
                return TradeAction.DO_NOTHING

            if self.require_model_agreement:
                if action == TradeAction.GO_LONG and not all(prediction >= self.min_model_confidence for prediction in valid_predictions):
                    self.logger.info(
                        f"Signal skipped for {symbol}: models do not agree on a qualified LONG "
                        f"(minimum per-model confidence {self.min_model_confidence:.2%})"
                    )
                    return TradeAction.DO_NOTHING
                if action == TradeAction.GO_SHORT and not all(prediction <= 1 - self.min_model_confidence for prediction in valid_predictions):
                    self.logger.info(
                        f"Signal skipped for {symbol}: models do not agree on a qualified SHORT "
                        f"(maximum per-model probability {1 - self.min_model_confidence:.2%})"
                    )
                    return TradeAction.DO_NOTHING
                
            # --- Multi-Timeframe Filter (Phase 2) ---
            if trend_context and action != TradeAction.DO_NOTHING:
                if trend_context == 'UP' and action == TradeAction.GO_LONG:
                    self.logger.info(f"Trend-aligned LONG accepted for {symbol}")
                elif trend_context == 'DOWN' and action == TradeAction.GO_SHORT:
                    self.logger.info(f"Trend-aligned SHORT accepted for {symbol}")
                else:
                    self.logger.info(
                        f"Counter-trend {action.name} accepted for {symbol} at "
                        f"{weighted_pred:.2%} confidence"
                    )

            # Apply Safety Filter
            if symbol and action != TradeAction.DO_NOTHING:
                sym_upper = symbol.upper()
                if "BOOM" in sym_upper and action == TradeAction.GO_LONG:
                    # Log internally if possible, but here we just block
                    self.logger.info(f"Signal skipped for {symbol}: LONG blocked by BOOM safety filter")
                    return TradeAction.DO_NOTHING # Block Buy on Boom
                if "CRASH" in sym_upper and action == TradeAction.GO_SHORT:
                    self.logger.info(f"Signal skipped for {symbol}: SHORT blocked by CRASH safety filter")
                    return TradeAction.DO_NOTHING # Block Sell on Crash
            
            return action
        
        return TradeAction.DO_NOTHING

class AnyStrongSignalStrategy(EnsembleStrategy):
    """
    Any Strong Signal Strategy: Maximum flexibility for capturing trades.
    
    Logic: Trade if ANY model shows high confidence (>58% or <42%)
    
    Benefits:
    - Captures trades when one model is very confident
    - Doesn't get cancelled out by disagreement
    - Still filters weak signals (both models must be uncertain to skip)
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        # Configurable thresholds
        signal_config = config.get('model', {}).get('any_strong_signal', {})
        self.buy_threshold = signal_config.get('buy_threshold', 0.58)
        self.sell_threshold = signal_config.get('sell_threshold', 0.42)
        self.logger.info(f"AnyStrongSignal Strategy: BUY>{self.buy_threshold}, SELL<{self.sell_threshold}")
        
    def get_decision(self, predictions: dict, position_info: dict, symbol: str = None, trend_context: str = None) -> TradeAction:
        has_position = position_info is not None
        
        # Filter out None/neutral predictions first
        valid_predictions = {}
        for model_name, pred in predictions.items():
            if pred is not None and pred != 0.5:
                valid_predictions[model_name] = pred
                
        if not valid_predictions:
            self.logger.warning("No valid predictions available")
            return TradeAction.DO_NOTHING
        
        # Check for exit first (if in position)
        if has_position:
            pos_side = position_info['side']
            
            # Exit if ANY model signals opposite direction
            if pos_side == 'long':
                if any(p < 0.5 for p in valid_predictions.values()):
                    return TradeAction.CLOSE_POSITION
            elif pos_side == 'short':
                if any(p > 0.5 for p in valid_predictions.values()):
                    return TradeAction.CLOSE_POSITION
        
        # Entry Logic: ANY strong signal triggers trade
        else:
            if not self._is_within_trading_hours():
                return TradeAction.DO_NOTHING
                
            max_prediction = max(valid_predictions.values())
            min_prediction = min(valid_predictions.values())
            
            action = TradeAction.DO_NOTHING
            
            # Check for strong BUY signal from any model
            if max_prediction >= self.buy_threshold:
                action = TradeAction.GO_LONG
                self.logger.info(f"Strong BUY signal: {max_prediction:.2%} (threshold: {self.buy_threshold:.2%})")
                
            # Check for strong SELL signal from any model
            elif min_prediction <= self.sell_threshold:
                action = TradeAction.GO_SHORT
                self.logger.info(f"Strong SELL signal: {min_prediction:.2%} (threshold: {self.sell_threshold:.2%})")
            
            # 1H Trend Filter removed by user request for testing phase

            # Apply Symbol Safety Filter
            if symbol and action != TradeAction.DO_NOTHING:
                sym_upper = symbol.upper()
                if "BOOM" in sym_upper and action == TradeAction.GO_LONG:
                    return TradeAction.DO_NOTHING
                if "CRASH" in sym_upper and action == TradeAction.GO_SHORT:
                    return TradeAction.DO_NOTHING
            
            return action
        
        return TradeAction.DO_NOTHING

# The MovingAverageCrossover strategy would need to be adapted to this new structure
# For now, it is left as-is to focus on the AI strategy refactoring.
# A full refactor would involve making it also return TradeAction enums.
class MovingAverageCrossover:
    pass

if __name__ == "__main__":
    print("This module defines strategy logic classes.")