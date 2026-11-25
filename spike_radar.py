"""
Boom 1000 & Crash 1000 Real-Time Spike Radar (Phone + Laptop, 24/7 Cloud-Ready)
===============================================================================
Streams live M5 candles from MetaTrader 5 (locally on Windows) or Deriv's
public WebSocket API (24/7 on free Linux cloud such as Render.com).

Alert Logic (Matches Phone Chart: M5 + Bollinger Bands 18, 2.0 + RSI 14):
  1. BOOM 1000 (BOOM1000):
     - Live upward spike >= boom_min_spike_pts (default 5.0 pts)
     - Price convincingly pierces Upper Bollinger Band(18, 2.0) by >= 2.0 pts
     - Live M5 RSI(14) >= 67.0 (exact MT5 SMMA Wilder formula)
     -> Fires INSTANT Phone (`ntfy`) + Laptop (Beep + Windows Notification) alert (<1s)!
     -> Sends a "COOLDOWN DONE" follow-up if price drifts cleanly red for 60s with zero follow-up spike.

  2. CRASH 1000 (CRASH1000):
     - Live downward crash >= crash_min_spike_pts (default 2.5 pts)
     - Price convincingly pierces Lower Bollinger Band(18, 2.0) by >= 1.0 pt
     - Live M5 RSI(14) <= 33.0 (exact MT5 SMMA Wilder formula)
     -> Fires INSTANT Phone (`ntfy`) + Laptop alert (<1s) + 60s Cooldown Done follow-up!

Usage:
  python spike_radar.py          # Start live 24/7 Spike Radar
  python spike_radar.py --test   # Send an instant test alert to your phone & laptop
  python spike_radar.py --smoke  # Connect to live feed, verify indicators & exit
"""

import asyncio
import json
import logging
import math
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("spike_radar")

DERIV_APP_ID = os.environ.get("DERIV_APP_ID", "1089").strip()
DERIV_WS_URLS = [
    f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}",
    f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}",
]
SYMBOL_LABELS = {
    "BOOM1000": "Boom 1000 Index",
    "CRASH1000": "Crash 1000 Index",
}
MT5_SYMBOL_MAP = {
    "BOOM1000": "Boom 1000 Index",
    "CRASH1000": "Crash 1000 Index",
}


def load_radar_config() -> dict:
    defaults = {
        "timeframe": "M5",
        "ntfy_topic": "YOUR_PRIVATE_NTFY_TOPIC",
        "ntfy_server": "https://ntfy.sh",
        "boom_rsi_min": 67.0,
        "crash_rsi_max": 33.0,
        "boom_min_spike_pts": 5.0,
        "crash_min_spike_pts": 2.5,
        "boom_bb_min_pierce_pts": 2.0,
        "crash_bb_min_pierce_pts": 1.0,
        "bb_period": 18,
        "bb_std": 2.0,
        "rsi_period": 14,
        "cooldown_seconds": 60,
        "alert_on_cooldown_ready": True,
        "laptop_sound": True,
        "laptop_popup": True,
    }
    cfg_path = Path(__file__).parent / "config.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                full = json.load(f)
            defaults.update(full.get("spike_radar", {}))
        except Exception as e:
            log.warning(f"Could not read config.json ({e}); using defaults.")

    # Environment variable overrides for 24/7 Cloud Hosting (Render / Koyeb / Railway / Fly.io)
    if os.environ.get("RADAR_TIMEFRAME"):
        defaults["timeframe"] = os.environ["RADAR_TIMEFRAME"].strip().upper()
    if os.environ.get("NTFY_TOPIC"):
        defaults["ntfy_topic"] = os.environ["NTFY_TOPIC"].strip()
    if os.environ.get("NTFY_SERVER"):
        defaults["ntfy_server"] = os.environ["NTFY_SERVER"].strip().rstrip("/")
    if os.environ.get("BB_PERIOD"):
        defaults["bb_period"] = int(os.environ["BB_PERIOD"])
    if os.environ.get("BB_STD"):
        defaults["bb_std"] = float(os.environ["BB_STD"])
    if os.environ.get("BOOM_RSI_MIN"):
        defaults["boom_rsi_min"] = float(os.environ["BOOM_RSI_MIN"])
    if os.environ.get("CRASH_RSI_MAX"):
        defaults["crash_rsi_max"] = float(os.environ["CRASH_RSI_MAX"])
    if os.environ.get("BOOM_BB_MIN_PIERCE"):
        defaults["boom_bb_min_pierce_pts"] = float(os.environ["BOOM_BB_MIN_PIERCE"])
    if os.environ.get("CRASH_BB_MIN_PIERCE"):
        defaults["crash_bb_min_pierce_pts"] = float(os.environ["CRASH_BB_MIN_PIERCE"])
    return defaults


def get_timeframe_granularity(tf: str) -> int:
    return {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}.get(tf.upper(), 300)


# ------------------------------------------------------------------
# Pure-Python Indicators (exact MT5 Bollinger ddof=0 & exact MT5 SMMA RSI)
# ------------------------------------------------------------------
def compute_bollinger(closes: List[float], period: int = 18, num_std: float = 2.0) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    mean = sum(window) / period
    # Population std (ddof=0) matches MetaTrader 5 built-in Bollinger Bands exactly
    var = sum((x - mean) ** 2 for x in window) / period
    sd = math.sqrt(var)
    return mean + num_std * sd, mean, mean - num_std * sd


def compute_rsi_wilder(closes: List[float], period: int = 14) -> Optional[float]:
    """Exact MetaTrader 5 built-in RSI (first N-bar SMA seed + Wilder SMMA)."""
    if len(closes) < period + 2:
        return None
    diffs = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in diffs]
    losses = [-d if d < 0 else 0.0 for d in diffs]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(diffs)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ------------------------------------------------------------------
# Dual Notification Dispatcher: Phone (`ntfy`) + Laptop (Sound/Popup)
# ------------------------------------------------------------------
class AlertDispatcher:
    def __init__(self, cfg: dict):
        self.ntfy_server = cfg["ntfy_server"].rstrip("/")
        self.ntfy_topic = cfg["ntfy_topic"]
        self.laptop_sound = bool(cfg.get("laptop_sound", True)) and platform.system() == "Windows"
        self.laptop_popup = bool(cfg.get("laptop_popup", True)) and platform.system() == "Windows"

    def send(self, title: str, message: str, priority: str = "high", tags: str = "chart_with_upwards_trend", is_boom: bool = True):
        log.info(f"[ALERT] {title} :: {message}")
        # Run network + Windows UI calls in background threads so WebSocket never stalls
        threading.Thread(
            target=self._send_ntfy, args=(title, message, priority, tags), daemon=True
        ).start()
        if self.laptop_sound:
            threading.Thread(target=self._play_sound, args=(is_boom,), daemon=True).start()
        if self.laptop_popup:
            threading.Thread(target=self._show_windows_popup, args=(title, message), daemon=True).start()

    def _send_ntfy(self, title: str, message: str, priority: str, tags: str) -> bool:
        url = f"{self.ntfy_server}/{self.ntfy_topic}"
        try:
            resp = requests.post(
                url,
                data=message.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": priority,
                    "Tags": tags,
                },
                timeout=8,
            )
            if resp.status_code == 200:
                log.info(f"[PHONE PUSH OK] Delivered to ntfy topic '{self.ntfy_topic}'")
                return True
            log.warning(f"[PHONE PUSH WARN] ntfy returned HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as e:
            log.error(f"[PHONE PUSH ERROR] Failed to reach ntfy: {e}")
        return False

    @staticmethod
    def _play_sound(is_boom: bool):
        try:
            import winsound
            freqs = [900, 1200, 1500] if is_boom else [1400, 1050, 750]
            for f in freqs:
                winsound.Beep(f, 160)
                time.sleep(0.05)
        except Exception:
            pass

    @staticmethod
    def _show_windows_popup(title: str, message: str):
        try:
            safe_title = title.replace("'", "").replace('"', "")
            safe_msg = message.replace("'", "").replace('"', "").replace("\n", " | ")
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$n = New-Object System.Windows.Forms.NotifyIcon; "
                "$n.Icon = [System.Drawing.SystemIcons]::Information; "
                "$n.Visible = $true; "
                f"$n.ShowBalloonTip(7000, '{safe_title}', '{safe_msg}', [System.Windows.Forms.ToolTipIcon]::Info); "
                "Start-Sleep -Seconds 8; $n.Dispose()"
            )
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-NoProfile", "-Command", ps],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


# ------------------------------------------------------------------
# Optional Healthcheck & Live Status HTTP Server (for 24/7 Cloud Hosting)
# ------------------------------------------------------------------
def start_health_server_if_cloud(radar: "SpikeRadar"):
    port_str = os.environ.get("PORT")
    if not port_str:
        return
    port = int(port_str)
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    class _HealthHandler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

        def do_GET(self):
            topic = radar.cfg.get("ntfy_topic", "")
            payload = {
                "status": "ALIVE",
                "started_at": started_at,
                "timeframe": radar.cfg.get("timeframe", "M5"),
                "bb": f"{radar.cfg.get('bb_period', 18)}, {radar.cfg.get('bb_std', 2.0)}",
                "ntfy_topic_set": bool(topic and topic != "YOUR_PRIVATE_NTFY_TOPIC"),
                "ws_connected": radar.ws_connected,
                "last_error": radar.last_error,
                "alerts_sent": radar.alerts_sent_count,
                "last_alert": radar.last_alert_summary,
                "live": radar.get_live_snapshot(),
            }
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    srv = HTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log.info(f"[CLOUD] Health & status server listening on port {port}")


# ------------------------------------------------------------------
# Core Real-Time Spike Radar Engine
# ------------------------------------------------------------------
class SpikeRadar:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.alerts = AlertDispatcher(cfg)
        self.candles: Dict[str, List[dict]] = {"BOOM1000": [], "CRASH1000": []}
        self.alerted_epochs: Dict[str, int] = {}
        # Pending cooldown watch: symbol -> dict(spike_epoch, spike_extreme, spike_pts)
        self.pending_cooldown: Dict[str, Optional[dict]] = {"BOOM1000": None, "CRASH1000": None}
        self._last_heartbeat = 0.0
        self.alerts_sent_count = 0
        self.last_alert_summary = "None yet"
        self.ws_connected = False
        self.last_error = None

    def get_live_snapshot(self) -> dict:
        snap = {}
        for sym in ("BOOM1000", "CRASH1000"):
            buf = self.candles.get(sym, [])
            if len(buf) >= 25:
                closes = [b["close"] for b in buf]
                up_bb, mid_bb, lo_bb = compute_bollinger(closes, self.cfg["bb_period"], self.cfg["bb_std"])
                r = compute_rsi_wilder(closes, self.cfg["rsi_period"])
                snap[sym] = {
                    "price": round(closes[-1], 2),
                    "rsi": round(r, 1) if r is not None else None,
                    "upper_bb": round(up_bb, 2) if up_bb is not None else None,
                    "lower_bb": round(lo_bb, 2) if lo_bb is not None else None,
                }
        return snap

    def _upsert_candle(self, sym: str, bar: dict) -> Optional[dict]:
        """Update live candle or append new candle. Returns just-closed previous bar if a new minute began."""
        buf = self.candles[sym]
        closed_prev = None
        if not buf:
            buf.append(bar)
        elif bar["epoch"] == buf[-1]["epoch"]:
            buf[-1] = bar
        elif bar["epoch"] > buf[-1]["epoch"]:
            closed_prev = buf[-1]
            buf.append(bar)
            if len(buf) > 120:
                del buf[:-120]
        return closed_prev

    def _check_cooldown_timer(self, sym: str):
        """60s after a qualified spike alert, confirm price drifted cleanly with NO secondary spike."""
        if not self.cfg.get("alert_on_cooldown_ready", True):
            return
        pending = self.pending_cooldown.get(sym)
        if not pending:
            return
        cool_secs = float(self.cfg.get("cooldown_seconds", 60))
        if time.time() - pending["alert_ts"] < cool_secs:
            return
        buf = self.candles.get(sym, [])
        if not buf:
            return
        live = buf[-1]
        self.pending_cooldown[sym] = None
        is_boom = sym == "BOOM1000"
        curr_p = live["close"]
        # Cancel cooldown ping if a secondary spike pushed beyond the original spike extreme
        if is_boom and (live["high"] > pending["spike_extreme"] + 1.0 or curr_p >= pending["spike_price"] - 0.25):
            log.info(f"[{sym}] Cooldown cancelled (secondary spike or no clean red drift after {int(cool_secs)}s).")
            return
        if (not is_boom) and (live["low"] < pending["spike_extreme"] - 0.5 or curr_p <= pending["spike_price"] + 0.12):
            log.info(f"[{sym}] Cooldown cancelled (secondary crash or no clean green drift after {int(cool_secs)}s).")
            return

        label = SYMBOL_LABELS[sym]
        drift_pts = abs(curr_p - pending["spike_price"])
        self.alerts_sent_count += 1
        self.last_alert_summary = f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} {label} COOLDOWN DONE ({drift_pts:.2f}pts)"
        self.alerts.send(
            title=f"{label} COOLDOWN DONE [OK]",
            message=(
                f"{int(cool_secs)}s clean {'RED' if is_boom else 'GREEN'} cooldown confirmed ({drift_pts:.2f} pts drift, "
                f"no follow-up spike) after {pending['spike_pts']:.1f}pt spike! Price: {curr_p:.2f}"
            ),
            priority="default",
            tags="white_check_mark",
            is_boom=is_boom,
        )

    def _evaluate_live(self, sym: str):
        buf = self.candles[sym]
        if len(buf) < max(25, self.cfg["bb_period"] + 5):
            return
        self._check_cooldown_timer(sym)
        live = buf[-1]
        closes = [b["close"] for b in buf]
        up_bb, mid_bb, lo_bb = compute_bollinger(closes, self.cfg["bb_period"], self.cfg["bb_std"])
        rsi_val = compute_rsi_wilder(closes, self.cfg["rsi_period"])
        if up_bb is None or rsi_val is None:
            return

        tf_lbl = self.cfg.get("timeframe", "M5")
        is_boom = sym == "BOOM1000"
        if is_boom:
            # Measure true upward spike impulse inside the live candle (works even if M5 drifted down before spiking!)
            spike_pts = live["close"] - live["low"]
            bb_pierce = live["close"] - up_bb
            min_pierce = float(self.cfg.get("boom_bb_min_pierce_pts", 2.0))
            triggered = (
                spike_pts >= self.cfg["boom_min_spike_pts"]
                and bb_pierce >= min_pierce
                and rsi_val >= self.cfg["boom_rsi_min"]
            )
        else:
            spike_pts = live["high"] - live["close"]
            bb_pierce = lo_bb - live["close"]
            min_pierce = float(self.cfg.get("crash_bb_min_pierce_pts", 1.0))
            triggered = (
                spike_pts >= self.cfg["crash_min_spike_pts"]
                and bb_pierce >= min_pierce
                and rsi_val <= self.cfg["crash_rsi_max"]
            )

        # Deduplicate: max 1 spike alert per candle (or allow re-alert only if a brand-new bigger spike hits >45s later)
        last_ep = self.alerted_epochs.get(sym)
        if triggered and last_ep != live["epoch"]:
            self.alerted_epochs[sym] = live["epoch"]
            label = SYMBOL_LABELS[sym]
            bb_lvl = up_bb if is_boom else lo_bb
            self.pending_cooldown[sym] = {
                "spike_epoch": live["epoch"],
                "spike_extreme": live["high"] if is_boom else live["low"],
                "spike_price": live["close"],
                "spike_pts": spike_pts,
                "alert_ts": time.time(),
            }
            self.alerts_sent_count += 1
            self.last_alert_summary = f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} {label} [{tf_lbl}] {'+' if is_boom else '-'}{spike_pts:.1f}pts BB+{bb_pierce:.1f} RSI={rsi_val:.1f}"
            self.alerts.send(
                title=f"{'BOOM' if is_boom else 'CRASH'} 1000 [{tf_lbl}] SPIKE ALERT!",
                message=(
                    f"{label} ({tf_lbl}): {'+' if is_boom else '-'}{spike_pts:.1f} pts spike @ {live['close']:.2f}\n"
                    f"{tf_lbl} RSI({self.cfg['rsi_period']}): {rsi_val:.1f} | Pierced {'Upper' if is_boom else 'Lower'} BB({self.cfg['bb_period']},{self.cfg['bb_std']:.1f}) @ {bb_lvl:.2f} by +{bb_pierce:.1f} pts [OK]\n"
                    f"Wait for 1m clean {'RED' if is_boom else 'GREEN'} cooldown before acting."
                ),
                priority="high",
                tags="rotating_light,chart_with_upwards_trend" if is_boom else "rotating_light,chart_with_downwards_trend",
                is_boom=is_boom,
            )

        # Log quiet status heartbeat every 5 minutes so user sees radar is alive
        now_t = time.time()
        if now_t - self._last_heartbeat >= 300:
            self._last_heartbeat = now_t
            self._log_status_line()

    def _log_status_line(self):
        parts = []
        for sym in ("BOOM1000", "CRASH1000"):
            buf = self.candles[sym]
            if len(buf) >= 25:
                closes = [b["close"] for b in buf]
                up_bb, _, lo_bb = compute_bollinger(closes, self.cfg["bb_period"], self.cfg["bb_std"])
                r = compute_rsi_wilder(closes, self.cfg["rsi_period"])
                parts.append(f"{sym}: {closes[-1]:.2f} (RSI={r:.1f}, BB={lo_bb:.1f}..{up_bb:.1f})")
        if parts:
            log.info("[RADAR LIVE] " + " | ".join(parts))

    def run_mt5(self, smoke_only: bool = False) -> bool:
        """Primary local Windows feed: polls live MetaTrader 5 M1 candles every 1 second (zero impact on Forex bot)."""
        try:
            import MetaTrader5 as mt5
        except ImportError:
            return False

        cfg_path = Path(__file__).parent / "config.json"
        mt5_cfg = {}
        if cfg_path.exists():
            try:
                mt5_cfg = json.loads(cfg_path.read_text(encoding="utf-8")).get("brokers", {}).get("mt5", {})
            except Exception:
                pass

        if mt5_cfg.get("login") and mt5_cfg.get("password") and mt5_cfg.get("server"):
            ok = mt5.initialize(
                login=int(mt5_cfg["login"]),
                password=mt5_cfg["password"],
                server=mt5_cfg["server"],
            )
        else:
            ok = mt5.initialize()

        if not ok:
            log.warning(f"MT5 unavailable ({mt5.last_error()}); falling back to Deriv Cloud WebSocket...")
            return False

        for code, mt5_sym in MT5_SYMBOL_MAP.items():
            mt5.symbol_select(mt5_sym, True)

        tf_str = self.cfg.get("timeframe", "M5").upper()
        mt5_tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
        }
        mt5_tf = mt5_tf_map.get(tf_str, mt5.TIMEFRAME_M5)

        log.info(
            f"[READY - MT5 LIVE {tf_str}] Watching Boom 1000 (Upper BB({self.cfg['bb_period']},{self.cfg['bb_std']}) + RSI>={self.cfg['boom_rsi_min']}) & "
            f"Crash 1000 (Lower BB({self.cfg['bb_period']},{self.cfg['bb_std']}) + RSI<={self.cfg['crash_rsi_max']}) every 1s -> ntfy '{self.cfg['ntfy_topic']}'"
        )

        initialized_syms = set()
        try:
            while True:
                for code, mt5_sym in MT5_SYMBOL_MAP.items():
                    rates = mt5.copy_rates_from_pos(mt5_sym, mt5_tf, 0, 120)
                    if rates is None or len(rates) < 25:
                        continue
                    bars = [
                        {
                            "epoch": int(r["time"]),
                            "open": float(r["open"]),
                            "high": float(r["high"]),
                            "low": float(r["low"]),
                            "close": float(r["close"]),
                        }
                        for r in rates
                    ]
                    if code not in initialized_syms:
                        self.candles[code] = bars
                        initialized_syms.add(code)
                        if len(initialized_syms) == 2:
                            self._log_status_line()
                            if smoke_only:
                                log.info(f"[SMOKE TEST PASSED] Live MT5 {tf_str} stream & BB({self.cfg['bb_period']},{self.cfg['bb_std']})/RSI verified!")
                                return True
                    else:
                        prev_epoch = self.candles[code][-1]["epoch"]
                        live_bar = bars[-1]
                        if live_bar["epoch"] > prev_epoch:
                            self.candles[code] = bars
                        else:
                            self.candles[code][-1] = live_bar
                        self._evaluate_live(code)
                time.sleep(1.0)
        except KeyboardInterrupt:
            log.info("Spike Radar stopped by user.")
            return True

    async def run(self, smoke_only: bool = False):
        backoff = 3
        url_idx = 0
        while True:
            ws_url = DERIV_WS_URLS[url_idx % len(DERIV_WS_URLS)]
            url_idx += 1
            try:
                log.info(f"Connecting to Deriv Live WebSocket ({ws_url})...")
                async with websockets.connect(ws_url, ping_interval=25, ping_timeout=15) as ws:
                    self.ws_connected = True
                    self.last_error = None
                    backoff = 3
                    tf_str = self.cfg.get("timeframe", "M5").upper()
                    gran = get_timeframe_granularity(tf_str)
                    for sym in ("BOOM1000", "CRASH1000"):
                        req = {
                            "ticks_history": sym,
                            "adjust_start_time": 1,
                            "count": 120,
                            "end": "latest",
                            "granularity": gran,
                            "style": "candles",
                            "subscribe": 1,
                        }
                        await ws.send(json.dumps(req))
                    log.info(
                        f"[READY - CLOUD WS {tf_str}] Watching BOOM1000 (Upper BB({self.cfg['bb_period']},{self.cfg['bb_std']}) + RSI>={self.cfg['boom_rsi_min']}) & "
                        f"CRASH1000 (Lower BB({self.cfg['bb_period']},{self.cfg['bb_std']}) + RSI<={self.cfg['crash_rsi_max']}) -> ntfy '{self.cfg['ntfy_topic']}'"
                    )

                    got_history = set()
                    async for raw in ws:
                        data = json.loads(raw)
                        if "error" in data:
                            err_msg = data["error"].get("message", "Unknown WS error")
                            self.last_error = err_msg
                            log.error(f"Deriv WS Error: {err_msg}")
                            continue

                        msg_type = data.get("msg_type")
                        if msg_type == "candles":
                            sym = data.get("echo_req", {}).get("ticks_history")
                            if sym in self.candles:
                                self.candles[sym] = [
                                    {
                                        "epoch": int(c["epoch"]),
                                        "open": float(c["open"]),
                                        "high": float(c["high"]),
                                        "low": float(c["low"]),
                                        "close": float(c["close"]),
                                    }
                                    for c in data.get("candles", [])
                                ]
                                got_history.add(sym)
                                if len(got_history) == 2:
                                    self._log_status_line()
                                    if smoke_only:
                                        log.info("[SMOKE TEST PASSED] Live Deriv stream & BB/RSI indicators verified!")
                                        return

                        elif msg_type == "ohlc":
                            ohlc = data["ohlc"]
                            sym = ohlc["symbol"]
                            if sym in self.candles:
                                bar = {
                                    "epoch": int(ohlc["open_time"]),
                                    "open": float(ohlc["open"]),
                                    "high": float(ohlc["high"]),
                                    "low": float(ohlc["low"]),
                                    "close": float(ohlc["close"]),
                                }
                                self._upsert_candle(sym, bar)
                                self._evaluate_live(sym)

            except KeyboardInterrupt:
                log.info("Spike Radar stopped by user.")
                return
            except Exception as e:
                self.ws_connected = False
                self.last_error = str(e)
                log.warning(f"WebSocket disconnected ({e}). Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)


def main():
    cfg = load_radar_config()
    if "--test" in sys.argv:
        dispatcher = AlertDispatcher(cfg)
        log.info(f"Sending test alert to ntfy topic '{cfg['ntfy_topic']}' + laptop...")
        ok = dispatcher._send_ntfy(
            "Spike Radar Test [OK]",
            "Your Boom 1000 & Crash 1000 Spike Radar is connected! You will get <1s alerts right here.",
            "high",
            "bell,white_check_mark",
        )
        if dispatcher.laptop_sound:
            dispatcher._play_sound(True)
        if dispatcher.laptop_popup:
            dispatcher._show_windows_popup(
                "Spike Radar Test [OK]",
                f"Phone push ({cfg['ntfy_topic']}): {'OK' if ok else 'FAILED'} | Ready for Boom & Crash spikes!",
            )
            time.sleep(2)
        sys.exit(0 if ok else 1)

    source_mode = os.environ.get("RADAR_SOURCE", "auto").lower()

    if "--smoke" in sys.argv:
        radar = SpikeRadar(cfg)
        if source_mode in ("auto", "mt5") and platform.system() == "Windows":
            if radar.run_mt5(smoke_only=True):
                return
        asyncio.run(radar.run(smoke_only=True))
        return

    radar = SpikeRadar(cfg)
    start_health_server_if_cloud(radar)
    if source_mode in ("auto", "mt5") and platform.system() == "Windows":
        if radar.run_mt5(smoke_only=False):
            return
    asyncio.run(radar.run(smoke_only=False))


if __name__ == "__main__":
    main()
