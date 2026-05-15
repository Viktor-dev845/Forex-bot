"use client";

import { useState } from "react";
import { useTradingStore } from "@/store/tradingStore";
import { Play, Square, AlertTriangle, ShieldAlert, Cpu, Settings, Terminal, Activity } from "lucide-react";
import { motion } from "framer-motion";

export default function SettingsPage() {
  const [loadingCmd, setLoadingCmd] = useState(false);
  const isConnected = useTradingStore(state => state.isConnected);
  const botState = useTradingStore(state => state.botState);
  
  const sendCommand = async (cmd: string) => {
    setLoadingCmd(true);
    try {
      await fetch('http://localhost:8000/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      });
    } catch (err) {
      console.error("Command failed", err);
    } finally {
      setLoadingCmd(false);
    }
  };

  const isRunning = botState?.is_running;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-8 max-w-5xl mx-auto"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <Settings className="text-slate-400" />
            System Control
          </h1>
          <p className="text-slate-500 text-sm font-medium mt-1">Engine orchestration and safety parameters</p>
        </div>
        
        <div className={`flex items-center gap-3 px-4 py-2 rounded-xl border ${isRunning ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-rose-500/5 border-rose-500/20'}`}>
           <div className="flex flex-col items-end">
              <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Engine Status</span>
              <span className={`text-xs font-bold ${isRunning ? 'text-emerald-400' : 'text-rose-400'}`}>
                {isRunning ? 'EXECUTING' : 'IDLE'}
              </span>
           </div>
           <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Col: Master Switch */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="glass-bright rounded-2xl p-8 border border-white/[0.03] shadow-xl relative overflow-hidden">
            <div className="flex items-center gap-4 mb-8">
               <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center">
                  <Cpu className="text-indigo-400" />
               </div>
               <div>
                  <h2 className="text-lg font-black text-white tracking-tight">Core Execution Engine</h2>
                  <p className="text-xs text-slate-500 font-medium">Master control for the trading loop</p>
               </div>
            </div>
            
            <div className="flex flex-col gap-8">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
                <div className="max-w-md">
                  <h3 className="text-white font-bold text-sm mb-1 uppercase tracking-wide">Live Trading Toggle</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Start or stop the core execution engine. When stopped, the bot will not place new trades but will continue monitoring open positions.
                  </p>
                </div>
                
                <div className="flex gap-4 shrink-0">
                  <button
                    onClick={() => sendCommand('RUN')}
                    disabled={loadingCmd || !isConnected || isRunning}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl font-black text-[10px] uppercase tracking-widest bg-emerald-500 text-white hover:bg-emerald-400 shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-30 disabled:grayscale"
                  >
                    <Play size={16} fill="currentColor" />
                    Start
                  </button>
                  
                  <button
                    onClick={() => sendCommand('STOP')}
                    disabled={loadingCmd || !isConnected || !isRunning}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl font-black text-[10px] uppercase tracking-widest bg-rose-500 text-white hover:bg-rose-400 shadow-lg shadow-rose-500/20 transition-all disabled:opacity-30 disabled:grayscale"
                  >
                    <Square size={16} fill="currentColor" />
                    Halt
                  </button>
                </div>
              </div>

              <div className="p-5 bg-amber-500/5 border border-amber-500/10 rounded-2xl flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center shrink-0">
                   <ShieldAlert className="text-amber-400" size={20} />
                </div>
                <div>
                  <h4 className="text-amber-400 font-black text-[10px] uppercase tracking-[0.2em] mb-1">Safety Override</h4>
                  <p className="text-xs text-amber-400/70 leading-relaxed">
                    Emergency halt will force all active threads to enter a cooldown state. This will persist across bot restarts until a manual RUN command is issued.
                  </p>
                </div>
              </div>
            </div>

            {/* Decorative background icon */}
            <Terminal size={120} className="absolute -right-8 -bottom-8 text-white/[0.02] -rotate-12 pointer-events-none" />
          </div>

          <div className="glass-bright rounded-2xl p-8 border border-white/[0.03] opacity-40 grayscale flex items-center justify-between">
             <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center">
                   <Activity size={18} className="text-slate-400" />
                </div>
                <div>
                   <h3 className="text-white font-bold text-sm tracking-tight">Auto-Retraining Module</h3>
                   <p className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Coming Soon</p>
                </div>
             </div>
             <div className="px-3 py-1 rounded bg-slate-800 text-[10px] font-black text-slate-500 tracking-[0.1em]">
                DISABLED
             </div>
          </div>
        </div>

        {/* Right Col: Diagnostics */}
        <div className="flex flex-col gap-6">
           <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-1">Diagnostics</h2>
           
           <div className="glass-bright rounded-2xl p-6 border border-white/[0.03] space-y-6">
              <div className="space-y-3">
                 <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest">
                    <span className="text-slate-500">API Latency</span>
                    <span className="text-emerald-400 font-mono">14ms</span>
                 </div>
                 <div className="w-full h-1 bg-white/[0.02] rounded-full overflow-hidden">
                    <div className="h-full w-[15%] bg-emerald-500" />
                 </div>
              </div>

              <div className="space-y-3">
                 <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest">
                    <span className="text-slate-500">WS Connection</span>
                    <span className="text-emerald-400 font-mono">STABLE</span>
                 </div>
                 <div className="w-full h-1 bg-white/[0.02] rounded-full overflow-hidden">
                    <div className="h-full w-full bg-emerald-500" />
                 </div>
              </div>

              <div className="space-y-3">
                 <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest">
                    <span className="text-slate-500">Model Memory</span>
                    <span className="text-indigo-400 font-mono">412MB</span>
                 </div>
                 <div className="w-full h-1 bg-white/[0.02] rounded-full overflow-hidden">
                    <div className="h-full w-[40%] bg-indigo-500" />
                 </div>
              </div>
              
              <div className="pt-4 border-t border-white/[0.03] mt-4">
                 <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-slate-500">Engine Build</span>
                    <span className="text-white mono">v2.4.1-async</span>
                 </div>
              </div>
           </div>

           <div className="glass-bright rounded-2xl p-6 border border-white/[0.03] flex flex-col gap-4">
              <div className="flex items-center gap-3">
                 <AlertTriangle size={16} className="text-rose-500" />
                 <span className="text-xs font-black text-white uppercase tracking-widest">Danger Zone</span>
              </div>
              <button className="w-full py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 font-black text-[10px] uppercase tracking-widest hover:bg-rose-500/20 transition-all">
                 Purge State & Restart
              </button>
           </div>
        </div>

      </div>
    </motion.div>
  );
}
