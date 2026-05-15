"use client";

import { motion } from "framer-motion";
import { Zap, TrendingUp, TrendingDown } from "lucide-react";

interface SignalGaugeProps {
  symbol: string;
  probability: number; // 0 to 1
  signal: 'UP' | 'DOWN' | 'NEUTRAL';
  price?: number;
}

export function SignalGauge({ symbol, probability, signal, price }: SignalGaugeProps) {
  const isBuy = signal === 'UP';
  const isNeutral = signal === 'NEUTRAL';
  
  // Calculate confidence (distance from 0.5)
  const confidence = Math.abs(probability - 0.5) * 2;
  const confidencePct = Math.round(confidence * 100);
  
  const colorClass = isNeutral ? 'bg-slate-500' : isBuy ? 'bg-emerald-500' : 'bg-rose-500';
  const textColor = isNeutral ? 'text-slate-400' : isBuy ? 'text-emerald-400' : 'text-rose-400';
  const Icon = isNeutral ? Zap : isBuy ? TrendingUp : TrendingDown;

  return (
    <motion.div 
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="glass-bright p-4 rounded-xl flex items-center justify-between group border border-white/[0.03] hover:border-indigo-500/30 transition-all"
    >
      <div className="flex items-center gap-4">
        <div className={`w-10 h-10 rounded-lg ${isNeutral ? 'bg-slate-500/10' : isBuy ? 'bg-emerald-500/10' : 'bg-rose-500/10'} flex items-center justify-center shrink-0`}>
          <Icon size={18} className={textColor} />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-white text-sm tracking-tight">{symbol.replace(' Index', '')}</span>
          <span className="text-[10px] text-slate-500 mono font-bold uppercase tracking-wider">
            {price ? price.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '---'}
          </span>
        </div>
      </div>
      
      <div className="flex flex-col items-end gap-1.5 w-1/3">
        <div className="flex justify-between w-full text-[10px] font-black uppercase tracking-widest">
          <span className={textColor}>{signal}</span>
          <span className="text-slate-500">{confidencePct}% CONF</span>
        </div>
        
        {/* Progress bar container */}
        <div className="w-full h-1.5 bg-white/[0.03] rounded-full overflow-hidden relative">
          <motion.div 
            className={`absolute top-0 bottom-0 ${colorClass} shadow-[0_0_8px_currentColor]`}
            initial={{ width: 0 }}
            animate={{ 
              width: `${confidencePct}%`,
              left: isBuy || isNeutral ? '0%' : 'auto',
              right: isBuy || isNeutral ? 'auto' : '0%'
            }}
            transition={{ type: "spring", stiffness: 80, damping: 20 }}
          />
        </div>
      </div>
    </motion.div>
  );
}
