"use client";

import { useEffect, useState } from "react";
import { useTradingStore, type TradeRecord, type PositionInfo } from "@/store/tradingStore";
import { format } from "date-fns";
import { 
  ArrowUpRight, ArrowDownRight, Clock, Shield, 
  History, Activity, Target, Briefcase 
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function TradesPage() {
  const [history, setHistory] = useState<TradeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  
  const botState = useTradingStore(state => state.botState);
  const ticks = useTradingStore(state => state.ticks);
  
  const fetchTrades = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/trades?limit=100');
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error("Failed to fetch trade history", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, 10000);
    return () => clearInterval(interval);
  }, []);

  // Filter out null positions and ensure we have a Record we can map over
  const positions = botState?.positions || {};
  const activeSymbols = Object.keys(positions).filter(sym => positions[sym] !== null);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-8"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <Briefcase className="text-amber-500" />
            Trade Journal
          </h1>
          <p className="text-slate-500 text-sm font-medium mt-1">Live exposure and verified execution logs</p>
        </div>
        
        <div className="flex items-center gap-3 bg-white/[0.03] px-4 py-2 rounded-xl border border-white/[0.05]">
           <div className="flex flex-col items-end">
              <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Active Exposure</span>
              <span className="text-white text-xs font-bold mono">{activeSymbols.length} POSITIONS</span>
           </div>
           <div className="w-px h-6 bg-white/10 mx-1" />
           <Activity size={18} className="text-emerald-500" />
        </div>
      </div>

      {/* Open Positions Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-1 flex flex-col gap-4">
          <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-1">Active Positions</h2>
          
          {activeSymbols.length === 0 ? (
            <div className="glass-bright rounded-2xl p-10 flex flex-col items-center justify-center text-center border border-white/[0.03]">
              <div className="w-12 h-12 rounded-full bg-white/[0.03] flex items-center justify-center mb-4 text-slate-600">
                <Target size={24} />
              </div>
              <p className="text-slate-400 font-bold text-sm">No Active Exposure</p>
              <p className="text-slate-600 text-xs mt-1">Bot is currently flat.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <AnimatePresence mode="popLayout">
                {activeSymbols.map(sym => {
                  const pos = positions[sym] as PositionInfo;
                  const entryPrice = botState?.entry_prices?.[sym] || 0;
                  const currentPrice = ticks[sym]?.price || entryPrice;
                  const isLong = pos.side === 'long';
                  
                  // Calculate unrealized P&L
                  const pnl = isLong 
                    ? (currentPrice - entryPrice) * pos.qty
                    : (entryPrice - currentPrice) * pos.qty;
                  const pnlPct = entryPrice > 0 ? (pnl / (entryPrice * pos.qty)) * 100 : 0;

                  return (
                    <motion.div
                      key={sym}
                      layout
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className={`glass-bright rounded-2xl p-5 border-l-4 ${isLong ? 'border-l-emerald-500' : 'border-l-rose-500'} border-y border-r border-white/[0.03]`}
                    >
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <p className="font-black text-white text-base tracking-tight">{sym.replace(' Index', '')}</p>
                          <span className={`text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded ${isLong ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                            {pos.side}
                          </span>
                        </div>
                        <div className="text-right">
                          <p className={`text-lg font-black mono ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {pnl >= 0 ? '+' : ''}{pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </p>
                          <p className={`text-[10px] font-bold mono ${pnl >= 0 ? 'text-emerald-500/70' : 'text-rose-500/70'}`}>
                            {pnlPct.toFixed(2)}%
                          </p>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1">
                           <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Entry</span>
                           <span className="text-xs text-white font-bold mono">{entryPrice.toLocaleString()}</span>
                        </div>
                        <div className="flex flex-col gap-1 text-right">
                           <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Current</span>
                           <span className="text-xs text-white font-bold mono">{currentPrice.toLocaleString()}</span>
                        </div>
                      </div>

                      <div className="mt-4 pt-4 border-t border-white/[0.03] flex items-center justify-between">
                         <div className="flex items-center gap-2 text-slate-500">
                            <Shield size={12} />
                            <span className="text-[9px] font-black uppercase tracking-widest">Protection</span>
                         </div>
                         <span className="text-[10px] text-slate-400 font-bold mono">
                            SL: {pos.sl_price?.toLocaleString() || 'NONE'}
                         </span>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Trade Journal (Right side) */}
        <div className="xl:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between px-1">
             <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Execution History</h2>
             <button onClick={fetchTrades} className="text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest flex items-center gap-1.5 transition-colors">
                <History size={12} />
                Refresh
             </button>
          </div>

          <div className="glass-bright rounded-2xl overflow-hidden border border-white/[0.03] shadow-2xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-white/[0.02] border-b border-white/[0.03]">
                    <th className="p-5 font-black text-slate-500 uppercase tracking-widest">Time</th>
                    <th className="p-5 font-black text-slate-500 uppercase tracking-widest">Asset</th>
                    <th className="p-5 font-black text-slate-500 uppercase tracking-widest">Action</th>
                    <th className="p-5 font-black text-slate-500 uppercase tracking-widest text-right">Execution</th>
                    <th className="p-5 font-black text-slate-500 uppercase tracking-widest text-right">Net P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.02]">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="p-10 text-center text-slate-500 font-bold">Initializing Journal Data...</td>
                    </tr>
                  ) : history.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-10 text-center text-slate-500 font-bold">No Records Found</td>
                    </tr>
                  ) : (
                    history.map((trade, i) => {
                      const isWin = trade.pnl && trade.pnl > 0;
                      const isLoss = trade.pnl && trade.pnl < 0;
                      
                      return (
                        <tr key={i} className="hover:bg-white/[0.01] transition-colors group">
                          <td className="p-5 text-slate-400 font-medium whitespace-nowrap">
                            {format(new Date(trade.timestamp), "MMM dd, HH:mm:ss")}
                          </td>
                          <td className="p-5 font-bold text-white whitespace-nowrap">
                            {trade.symbol.replace(' Index', '')}
                          </td>
                          <td className="p-5">
                            <span className={`text-[10px] font-black px-2 py-1 rounded tracking-widest ${
                              trade.side === 'BUY' ? 'text-emerald-400 bg-emerald-500/5' : 
                              trade.side === 'SELL' ? 'text-rose-400 bg-rose-500/5' :
                              'text-slate-300 bg-slate-800'
                            }`}>
                              {trade.side}
                            </span>
                          </td>
                          <td className="p-5 font-bold text-slate-300 text-right mono">
                             {trade.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                             <div className="text-[9px] text-slate-600 font-medium">{trade.quantity.toFixed(4)} UNITS</div>
                          </td>
                          <td className={`p-5 font-black text-right mono text-sm ${
                            isWin ? 'text-emerald-400' : isLoss ? 'text-rose-400' : 'text-slate-600'
                          }`}>
                            {trade.pnl ? (
                              <div className="flex flex-col items-end">
                                <span className="flex items-center gap-1">
                                  {isWin ? <ArrowUpRight size={14} /> : isLoss ? <ArrowDownRight size={14} /> : null}
                                  ${Math.abs(trade.pnl).toFixed(2)}
                                </span>
                              </div>
                            ) : '-'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
