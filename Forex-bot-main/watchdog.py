"""
BotWatchdog — Institutional-Grade Heartbeat & Failover Monitor

Runs in a background thread and independently monitors:
1. WebSocket/API liveness (ping Deriv every 5s)
2. Bot process health (main loop must update heartbeat every 90s)

On failure: triggers emergency safety lock (all open SL moved to Break-Even).

[ANTIGRAVITY_ACTIVE] - Phase 2 of Institutional Hardening
"""

import threading
import time
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger("watchdog")


class BotWatchdog:
    """
    Background watchdog that monitors bot health and triggers emergency protocols.
    Designed to be started once during TradingBot.__init__ and run forever.
    """

    DERIV_PING_URL = "https://api.deriv.com/ping"
    PING_INTERVAL_SECONDS = 5
    MAX_FAILED_PINGS = 3
    BOT_LIVENESS_TIMEOUT_SECONDS = 90

    def __init__(self, risk_manager, positions_ref: dict, symbols: list, monitor):
        """
        Args:
            risk_manager: The RiskManager instance (for emergency SL lock)
            positions_ref: Reference to bot.positions dict (live pointer, not copy)
            symbols: List of trading symbols
            monitor: BotMonitor instance for logging
        """
        self.risk_manager = risk_manager
        self.positions = positions_ref   # Live reference — always current
        self.symbols = symbols
        self.monitor = monitor

        self.last_heartbeat: datetime = datetime.now()
        self.running = False
        self._thread = None

        self._consecutive_ping_failures = 0
        self._emergency_active = False

    def start(self):
        """Start the watchdog in a daemon background thread."""
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="BotWatchdog")
        self._thread.start()
        logger.info("[WATCHDOG] Started. Monitoring bot liveness and API connectivity.")

    def stop(self):
        """Gracefully stop the watchdog."""
        self.running = False
        logger.info("[WATCHDOG] Stopped.")

    def update_heartbeat(self):
        """Call this at the top of every run_trading_cycle() to signal the bot is alive."""
        self.last_heartbeat = datetime.now()
        self._emergency_active = False  # Auto-reset on recovery

    def _run(self):
        """Main watchdog loop."""
        while self.running:
            try:
                self._check_api_liveness()
                self._check_bot_liveness()
            except Exception as e:
                logger.error(f"[WATCHDOG] Loop error: {e}")
            time.sleep(self.PING_INTERVAL_SECONDS)

    def _check_api_liveness(self):
        """Ping Deriv API. Trigger emergency lock after 3 consecutive failures."""
        try:
            resp = requests.get(self.DERIV_PING_URL, timeout=4)
            if resp.status_code == 200:
                if self._consecutive_ping_failures > 0:
                    logger.info(f"[WATCHDOG] API connectivity restored after {self._consecutive_ping_failures} failed pings.")
                self._consecutive_ping_failures = 0
                latency_ms = int(resp.elapsed.total_seconds() * 1000)
                logger.debug(f"[WATCHDOG] Heartbeat OK. API latency: {latency_ms}ms")
            else:
                self._consecutive_ping_failures += 1
        except Exception:
            self._consecutive_ping_failures += 1
            logger.warning(f"[WATCHDOG] API ping failed ({self._consecutive_ping_failures}/{self.MAX_FAILED_PINGS})")

        if self._consecutive_ping_failures >= self.MAX_FAILED_PINGS and not self._emergency_active:
            self._trigger_emergency_lock(reason="API connectivity lost")

    def _check_bot_liveness(self):
        """Check that the main trading loop is still running."""
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        if elapsed > self.BOT_LIVENESS_TIMEOUT_SECONDS and not self._emergency_active:
            self._trigger_emergency_lock(reason=f"Bot loop frozen ({elapsed:.0f}s since last heartbeat)")

    def _trigger_emergency_lock(self, reason: str):
        """
        Emergency Protocol: Move ALL open position Stop-Losses to Break-Even.
        This ensures no position is left unmanaged during a network/process failure.
        """
        self._emergency_active = True
        logger.critical(f"[WATCHDOG] *** EMERGENCY LOCK TRIGGERED *** Reason: {reason}")

        locked_count = 0
        for symbol in self.symbols:
            if self.positions.get(symbol) is not None:
                try:
                    self.risk_manager.move_to_break_even(symbol, current_price=None)
                    logger.warning(f"[WATCHDOG] Safety Lock applied to {symbol} — SL moved to Break-Even.")
                    locked_count += 1
                except Exception as e:
                    logger.error(f"[WATCHDOG] Failed to lock {symbol}: {e}")

        if locked_count > 0:
            logger.critical(f"[WATCHDOG] Emergency Lock complete. {locked_count} position(s) secured.")
        else:
            logger.info("[WATCHDOG] Emergency Lock triggered but no open positions to protect.")
