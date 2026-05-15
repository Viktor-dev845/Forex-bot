"use client";

import { useState } from "react";
import { CandlestickChart } from "@/components/CandlestickChart";
import { useTradingStore } from "@/store/tradingStore";
import { motion } from "framer-motion";
import { BarChart3, Activity, Clock, Layers } from "lucide-react";

export default function ChartsPage() {
  const [activeSymbol, setActiveSymbol] = useState("Volatility 75 Index");
  const [timeframe, setTimeframe] = useState("M5");
  
  const botState = useTradingStore(state => state.botState);
  const symbols = botState?.symbols || ["Volatility 75 Index", "Crash 500 Index", "Boom 1000 Index"];

  const timeframes = [
    { id: "M1", label: "1m" },
    { id: "M5", label: "5m" },
    { id: "M15", label: "15m" },
    { id: "H1", label: "1h" },
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col h-[calc(100vh-10rem)] gap-5"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <BarChart3 className="text-indigo-500" />
            Live Market Analysis
          </h1>
          <p className="text-slate-500 text-sm font-medium mt-1">Real-time charts with technical indicator overlays</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-white/[0.03] p-1 rounded-xl border border-white/[0.05]">
            {timeframes.map(tf => (
              <button
                key={tf.id}
                onClick={() => setTimeframe(tf.id)}
                className={`px-4 py-1.5 rounded-lg text-xs font-black uppercase tracking-widest transition-all ${
                  timeframe === tf.id
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-1 min-h-0">
        
        {/* Sidebar: Symbol Selection */}
        <div className="lg:col-span-3 flex flex-col gap-3">
          <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] px-1">Select Asset</p>
          <div className="flex flex-col gap-2">
            {symbols.map(sym => (
              <button
                key={sym}
                onClick={() => setActiveSymbol(sym)}
                className={`flex items-center justify-between p-4 rounded-xl border transition-all group ${
                  activeSymbol === sym 
                    ? 'bg-indigo-600/10 border-indigo-500/40 text-white shadow-lg shadow-indigo-600/5' 
                    : 'bg-white/[0.02] border-white/[0.05] text-slate-400 hover:bg-white/[0.04] hover:border-white/[0.1]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                    activeSymbol === sym ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-500 group-hover:bg-slate-700'
                  }`}>
                    <Activity size={16} />
                  </div>
                  <span className="font-bold text-sm">{sym.replace(' Index', '')}</span>
                </div>
                {activeSymbol === sym && (
                  <motion.div layoutId="active-indicator" className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8]" />
                )}
              </button>
            ))}
          </div>

          <div className="mt-auto glass-bright p-5 rounded-2xl border border-white/[0.03]">
             <div className="flex items-center gap-3 text-indigo-400 mb-3">
                <Layers size={18} />
                <span className="font-bold text-xs uppercase tracking-wider">Indicator Status</span>
             </div>
             <div className="space-y-3">
                <div className="flex justify-between text-[10px] font-bold">
                   <span className="text-slate-500 uppercase">LSTM Weight</span>
                   <span className="text-emerald-400">ACTIVE</span>
                </div>
                <div className="flex justify-between text-[10px] font-bold">
                   <span className="text-slate-500 uppercase">XGBoost Conf</span>
                   <span className="text-emerald-400">ACTIVE</span>
                </div>
                <div className="flex justify-between text-[10px] font-bold">
                   <span className="text-slate-500 uppercase">Fractal Sync</span>
                   <span className="text-amber-400">WAITING</span>
                </div>
             </div>
          </div>
        </div>

        {/* Center: Main Chart Area */}
        <div className="lg:col-span-9 flex flex-col gap-4 min-h-[500px]">
          <div className="glass-bright flex-1 rounded-2xl p-1 overflow-hidden relative border border-white/[0.03] shadow-2xl">
            {/* Header info overlay inside chart */}
            <div className="absolute top-6 left-6 z-10 pointer-events-none">
               <div className="flex items-center gap-3">
                  <h2 className="text-xl font-black text-white tracking-tighter">{activeSymbol}</h2>
                  <span className="px-2 py-0.5 rounded bg-white/10 text-[10px] font-black text-white uppercase tracking-widest backdrop-blur-md">
                     {timeframe}
                  </span>
               </div>
            </div>

            <div className="absolute top-6 right-6 z-10 pointer-events-none flex items-center gap-4">
               <div className="flex items-center gap-2 bg-black/40 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/5">
                  <div className="dot-live" />
                  <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Live Stream</span>
               </div>
            </div>

            {/* We use key to force unmount/remount when symbol changes to reset Lightweight Charts state completely */}
            <CandlestickChart key={`${activeSymbol}-${timeframe}`} symbol={activeSymbol} timeframe={timeframe} />
          </div>
          
          <div className="h-24 glass-bright rounded-2xl border border-white/[0.03] flex items-center px-8 justify-between">
             <div className="flex items-center gap-6">
                <div className="flex flex-col">
                   <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Chart Engine</span>
                   <span className="text-white text-xs font-bold">Lightweight Charts v5.1</span>
                </div>
                <div className="w-px h-8 bg-white/5" />
                <div className="flex flex-col">
                   <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Session Volume</span>
                   <span className="text-white text-xs font-bold mono">1.24M UNITS</span>
                </div>
             </div>
             <div className="flex items-center gap-2 text-slate-500 text-[10px] font-bold">
                <Clock size={14} />
                <span>LAST UPDATE: {new Date().toLocaleTimeString()}</span>
             </div>
          </div>
        </div>

      </div>
    </motion.div>
  );
}
