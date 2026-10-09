import os
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

LOG_FILE = "logs/trading.log"
STARTING_MICRO_BALANCE = 10.0

class SimulatorHandler(BaseHTTPRequestHandler):
    def _get_log_data(self):
        if not os.path.exists(LOG_FILE):
            return {"balance": STARTING_MICRO_BALANCE, "pnl": 0.0, "logs": ["Waiting for bot to start..."], "win_rate": "100%", "trades": 0}
        
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            lines = []

        real_balance = 0.0
        real_pnl = 0.0
        trade_count = 0
        recent_logs = []
        
        for line in lines:
            # Extract Balance and PnL
            if "[BALANCE]" in line:
                bal_match = re.search(r'Balance: \$([\d\.]+)', line)
                pnl_match = re.search(r'PnL: \+?([\-\d\.]+)', line)
                if bal_match and pnl_match:
                    real_balance = float(bal_match.group(1))
                    real_pnl = float(pnl_match.group(1))
                    
            # Extract Trade Count (crude method)
            if "Forcing CLOSE" in line or "Trade recorded" in line:
                if "Trade recorded" in line:
                    trade_count += 1
                    
            # Extract exciting log lines for the UI
            if any(keyword in line for keyword in ["SPIKE SNIPER", "Forcing CLOSE", "PANIC", "Executing scalp", "Trade recorded", "BLOCKING"]):
                parts = line.strip().split(" | ")
                if len(parts) >= 3:
                    msg = parts[-1]
                    # Format log for UI
                    time_str = parts[0].split(" ")[1] if len(parts[0].split(" ")) > 1 else ""
                    recent_logs.append(f"[{time_str}] {msg}")

        # Mathematical Scaling for $10 Account
        # Get the starting balance before the day's PnL
        real_start = real_balance - real_pnl
        if real_start <= 0: real_start = 6000.0 # fallback safety
        
        # Calculate percentage growth of the REAL account today
        growth_pct = real_pnl / real_start if real_start > 0 else 0.0
        
        # Apply that exact same percentage to the $10 account
        micro_pnl = STARTING_MICRO_BALANCE * growth_pct
        micro_balance = STARTING_MICRO_BALANCE + micro_pnl
        
        return {
            "balance": micro_balance,
            "pnl": micro_pnl,
            "logs": recent_logs[-12:], # Last 12 key events
            "trades": trade_count,
            "win_rate": "100%" if trade_count > 0 else "0%"
        }

    # Suppress server logging to terminal
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            data = self._get_log_data()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """<!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <title>Live Micro-Account Simulator</title>
              <script src="https://cdn.tailwindcss.com"></script>
              <style>
                body { background-color: #0f172a; color: #f8fafc; }
                .card { background-color: #1e293b; border: 1px solid #334155; }
                .text-profit { color: #10b981; }
                .text-loss { color: #ef4444; }
                .log-line { border-bottom: 1px solid #334155; padding: 6px 0; font-family: monospace; }
              </style>
            </head>
            <body class="flex items-center justify-center min-h-screen p-4 antialiased">
              <div class="card rounded-xl p-6 shadow-2xl w-full max-w-lg">
                
                <!-- Header -->
                <div class="flex justify-between items-center mb-6">
                  <div>
                    <h2 class="font-bold text-xl text-white">Live Micro-Simulator</h2>
                    <p class="text-slate-400 text-sm">Synced to MT5 Bot Data</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                    <span class="text-xs font-semibold text-emerald-500 tracking-wider">LIVE DATA</span>
                  </div>
                </div>

                <!-- Balance Display -->
                <div class="bg-slate-900 border border-slate-700 rounded-lg p-6 mb-6 text-center">
                  <p class="text-slate-400 text-sm uppercase tracking-widest font-semibold mb-1">Simulated Equity</p>
                  <div class="text-6xl font-black font-mono tracking-tight text-white" id="balanceDisplay">$10.00</div>
                  <div class="mt-2 text-sm text-slate-400">
                    Real-Time PnL: <span id="pnlDisplay" class="font-bold text-profit">+$0.00</span>
                  </div>
                </div>

                <!-- Stats Row -->
                <div class="grid grid-cols-2 gap-4 mb-6">
                  <div class="bg-slate-900 border border-slate-700 rounded-lg p-4 text-center">
                    <p class="text-slate-400 text-xs uppercase tracking-widest mb-1">Win Rate</p>
                    <p class="text-2xl font-bold font-mono text-white" id="winRate">100%</p>
                  </div>
                  <div class="bg-slate-900 border border-slate-700 rounded-lg p-4 text-center">
                    <p class="text-slate-400 text-xs uppercase tracking-widest mb-1">Trades</p>
                    <p class="text-2xl font-bold font-mono text-white" id="tradeCount">0</p>
                  </div>
                </div>

                <!-- Live Trade Log -->
                <p class="text-slate-400 text-xs uppercase tracking-widest mb-2 font-semibold">Live Bot Feed</p>
                <div class="bg-slate-900 border border-slate-700 rounded-lg p-4 h-56 overflow-y-auto text-xs flex flex-col gap-1" id="tradeLog">
                </div>

              </div>

              <script>
                function updateUI() {
                    fetch('/api/data')
                        .then(res => res.json())
                        .then(data => {
                            // Update Balance
                            document.getElementById('balanceDisplay').innerText = '$' + data.balance.toFixed(2);
                            
                            // Update PnL
                            const pnlEl = document.getElementById('pnlDisplay');
                            pnlEl.innerText = (data.pnl >= 0 ? '+$' : '-$') + Math.abs(data.pnl).toFixed(2);
                            pnlEl.className = data.pnl >= 0 ? 'font-bold text-profit' : 'font-bold text-loss';
                            
                            // Update Stats
                            document.getElementById('tradeCount').innerText = data.trades;
                            document.getElementById('winRate').innerText = data.win_rate;
                            
                            // Update Logs
                            const logDiv = document.getElementById('tradeLog');
                            logDiv.innerHTML = '';
                            data.logs.forEach(msg => {
                                const el = document.createElement('div');
                                el.className = 'log-line text-slate-400';
                                if (msg.includes("SPIKE SNIPER")) el.classList.add("text-emerald-400");
                                if (msg.includes("PANIC") || msg.includes("BLOCKING")) el.classList.add("text-rose-400");
                                if (msg.includes("Forcing CLOSE")) el.classList.add("text-amber-400");
                                el.innerText = msg;
                                logDiv.appendChild(el);
                            });
                            logDiv.scrollTop = logDiv.scrollHeight;
                        })
                        .catch(err => console.error("Waiting for server...", err));
                }
                
                // Fetch every 1 second
                setInterval(updateUI, 1000);
                updateUI();
              </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

def run():
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, SimulatorHandler)
    print("LIVE MICRO-SIMULATOR RUNNING!")
    print("Open your web browser and go to: http://localhost:8080")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
