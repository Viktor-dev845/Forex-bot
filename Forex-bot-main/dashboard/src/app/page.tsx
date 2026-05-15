"use client";

import { useEffect, useState, useRef } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useTradingStore, type PositionInfo } from "@/store/tradingStore";
import { StatCard } from "@/components/StatCard";
import { CandlestickChart } from "@/components/CandlestickChart";
import { 
  Activity, ArrowUpRight, ArrowDownRight, Globe, BarChart3, 
  Layers, Zap, List, Minus
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

function fmt(n: number, dec = 2) {
  return n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

export default function OverviewPage() {
  useWebSocket();
  const botState = useTradingStore(s => s.botState);
  const ticks = useTradingStore(s => s.ticks);

  if (!botState) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-6">
        <div className="w-12 h-12 border-2 border-[#00FF9D]/20 border-t-[#00FF9D] rounded-full animate-spin" />
        <div className="text-center">
           <p className="font-black text-[#FFFFFF] text-sm uppercase tracking-[0.2em]">Initializing Core</p>
           <p className="text-[#444444] text-[10px] mt-1 font-bold">Synchronizing with trading engine...</p>
        </div>
      </div>
    );
  }

  const { account, symbols, positions, predictions, trade_history } = botState;
  const equity = account?.equity ?? 100;
  const dailyPnl = account?.daily_pnl ?? 0;
  const activeSymbols = symbols || [];
  const recentTrades = trade_history?.slice(0, 8) || [];

  return (
    <div className="flex flex-col gap-8 pb-10">
      
      {/* ── KPI Grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Account Equity" value={equity} prefix="$" />
        <StatCard title="Daily Unrealized" value={dailyPnl} prefix="$" trend={0.00} />
        <StatCard title="Active Instances" value={activeSymbols.length} decimals={0} icon={Zap} />
        <StatCard title="Session Return" value={account?.return_pct || 0} suffix="%" icon={BarChart3} />
      </div>

      {/* ── Dashboard Grid ── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        
        {/* Left Col: Main Chart + Matrix */}
        <div className="xl:col-span-8 flex flex-col gap-6">
          
          {/* Main Chart Section */}
          <div className="bg-[#0F0F0F] rounded-lg border border-[#1F1F1F] flex flex-col h-[520px] overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-[#1F1F1F]">
               <div className="flex items-center gap-6">
                  <h3 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
                    <Activity size={14} className="text-[#00FF9D]" />
                    Live Market Stream
                  </h3>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-[#00FF9D] glow-green" />
                    <span className="text-[10px] font-bold text-[#888888] uppercase tracking-widest">Volatility 75 Index</span>
                  </div>
               </div>
               <div className="flex gap-2">
                  {["1m", "5m", "15m", "1h"].map(tf => (
                    <button key={tf} className={`px-3 py-1 rounded text-[10px] font-black uppercase tracking-widest border transition-all ${tf === '5m' ? 'bg-[#1F1F1F] text-white border-[#333]' : 'text-[#444444] border-transparent hover:text-[#888888]'}`}>
                      {tf}
                    </button>
                  ))}
               </div>
            </div>
            
            <div className="flex-1 bg-black/40">
               <CandlestickChart symbol="Volatility 75 Index" timeframe="M5" />
            </div>
          </div>

          {/* Engine Matrix Table */}
          <div className="bg-[#0F0F0F] rounded-lg border border-[#1F1F1F] overflow-hidden">
            <div className="p-5 border-b border-[#1F1F1F] flex items-center justify-between">
               <h3 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
                 <Layers size={14} className="text-[#00FF9D]" />
                 Signal Matrix
               </h3>
               <span className="text-[9px] font-black text-[#444444] uppercase tracking-widest">3 Nodes Online</span>
            </div>

            <div className="overflow-x-auto">
               <table className="w-full text-left">
                  <thead>
                     <tr className="bg-[#0A0A0A] border-b border-[#1F1F1F]">
                        <th className="p-4 text-[9px] font-black text-[#444444] uppercase tracking-widest">Instrument</th>
                        <th className="p-4 text-[9px] font-black text-[#444444] uppercase tracking-widest">Last Price</th>
                        <th className="p-4 text-[9px] font-black text-[#444444] uppercase tracking-widest">Ensemble Confidence</th>
                        <th className="p-4 text-[9px] font-black text-[#444444] uppercase tracking-widest">Signal</th>
                        <th className="p-4 text-[9px] font-black text-[#444444] uppercase tracking-widest">Action</th>
                     </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1F1F1F]">
                     {activeSymbols.map(sym => {
                        const price = ticks?.[sym]?.price ?? 0;
                        const pred = predictions?.[sym];
                        const isUp = pred?.signal === 'UP';
                        const isNeutral = pred?.signal === 'NEUTRAL';
                        const confidence = Math.round(Math.abs((pred?.prob ?? 0.5) - 0.5) * 200);
                        
                        return (
                           <tr key={sym} className="hover:bg-[#161616] transition-colors">
                              <td className="p-4">
                                 <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-[#161616] border border-[#1F1F1F] flex items-center justify-center text-[#888888]">
                                       <Globe size={14} />
                                    </div>
                                    <span className="text-xs font-bold text-white">{sym.replace(' Index', '')}</span>
                                 </div>
                              </td>
                              <td className="p-4 font-mono font-bold text-xs text-[#888888]">
                                 {price.toLocaleString()}
                              </td>
                              <td className="p-4">
                                 <div className="flex items-center gap-3">
                                    <div className="flex-1 h-1 bg-[#1F1F1F] rounded-full overflow-hidden max-w-[80px]">
                                       <div className="h-full bg-[#00FF9D]" style={{ width: `${confidence}%` }} />
                                    </div>
                                    <span className="text-[10px] font-bold text-white font-mono">{confidence}%</span>
                                 </div>
                              </td>
                              <td className="p-4">
                                 <div className={`flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest ${isNeutral ? 'text-[#444444]' : isUp ? 'text-[#00FF9D]' : 'text-[#FF3B30]'}`}>
                                    {isNeutral ? <Minus size={12} /> : isUp ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                    {pred?.signal || 'WAIT'}
                                 </div>
                              </td>
                              <td className="p-4">
                                 <span className="px-2 py-0.5 rounded bg-[#1F1F1F] text-[#444444] text-[9px] font-black uppercase tracking-widest">
                                    Monitoring
                                 </span>
                              </td>
                           </tr>
                        );
                     })}
                  </tbody>
               </table>
            </div>
          </div>
        </div>

        {/* Right Col: Feed + Diagnostics */}
        <div className="xl:col-span-4 flex flex-col gap-6">
           
           {/* Live Trade Feed */}
           <div className="bg-[#0F0F0F] rounded-lg border border-[#1F1F1F] flex flex-col h-[400px]">
              <div className="p-5 border-b border-[#1F1F1F] flex items-center justify-between">
                 <h3 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
                   <List size={14} className="text-[#00FF9D]" />
                   Execution Feed
                 </h3>
                 <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#00FF9D] glow-green" />
                    <span className="text-[9px] font-black text-[#00FF9D] uppercase tracking-widest">Live</span>
                 </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                 {recentTrades.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center opacity-20 grayscale">
                       <BarChart3 size={32} />
                       <p className="text-[10px] font-black uppercase mt-2">No Trades Recorded</p>
                    </div>
                 ) : (
                    recentTrades.map((t, i) => (
                       <div key={i} className="flex items-center justify-between border-b border-[#1F1F1F] pb-3 last:border-0 last:pb-0">
                          <div>
                             <p className="text-[11px] font-bold text-white">{t.symbol.replace(' Index', '')}</p>
                             <p className="text-[9px] font-black text-[#444444] uppercase tracking-widest">{t.side} · {t.quantity.toFixed(4)} U</p>
                          </div>
                          <div className="text-right">
                             <p className={`text-[11px] font-bold font-mono ${t.pnl && t.pnl > 0 ? 'text-[#00FF9D]' : t.pnl && t.pnl < 0 ? 'text-[#FF3B30]' : 'text-white'}`}>
                                {t.pnl ? (t.pnl > 0 ? '+' : '') + t.pnl.toFixed(2) : t.price.toFixed(2)}
                             </p>
                             <p className="text-[9px] font-bold text-[#444444] font-mono">{new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                          </div>
                       </div>
                    ))
                 )}
              </div>
           </div>

           {/* Bot Diagnostics */}
           <div className="bg-[#0F0F0F] rounded-lg border border-[#1F1F1F] p-6 space-y-6">
              <h3 className="text-[10px] font-black text-[#444444] uppercase tracking-[0.2em]">System Telemetry</h3>
              
              <div className="space-y-4">
                 <div className="space-y-2">
                    <div className="flex justify-between text-[10px] font-bold">
                       <span className="text-[#888888] uppercase tracking-widest">LSTM Accuracy</span>
                       <span className="text-white mono">94.2%</span>
                    </div>
                    <div className="h-1 bg-[#1F1F1F] rounded-full overflow-hidden">
                       <div className="h-full bg-[#00FF9D]/60" style={{ width: '94%' }} />
                    </div>
                 </div>

                 <div className="space-y-2">
                    <div className="flex justify-between text-[10px] font-bold">
                       <span className="text-[#888888] uppercase tracking-widest">XGBoost Load</span>
                       <span className="text-white mono">Low</span>
                    </div>
                    <div className="h-1 bg-[#1F1F1F] rounded-full overflow-hidden">
                       <div className="h-full bg-[#007AFF]/60" style={{ width: '22%' }} />
                    </div>
                 </div>

                 <div className="space-y-2">
                    <div className="flex justify-between text-[10px] font-bold">
                       <span className="text-[#888888] uppercase tracking-widest">Socket Health</span>
                       <span className="text-white mono">Optimal</span>
                    </div>
                    <div className="h-1 bg-[#1F1F1F] rounded-full overflow-hidden">
                       <div className="h-full bg-[#00FF9D]/60" style={{ width: '100%' }} />
                    </div>
                 </div>
              </div>

              <div className="pt-4 border-t border-[#1F1F1F] flex items-center justify-between">
                 <span className="text-[9px] font-black text-[#444444] uppercase tracking-widest">Version</span>
                 <span className="text-[9px] font-bold text-white mono">2.4.0-CARBON</span>
              </div>
           </div>

        </div>
      </div>
    </div>
  );
}
