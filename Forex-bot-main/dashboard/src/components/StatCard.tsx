"use client";

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface StatCardProps {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  trend?: number;
  decimals?: number;
  icon?: React.ElementType;
}

export function StatCard({ 
  title, 
  value, 
  prefix = "", 
  suffix = "", 
  trend, 
  decimals = 2,
  icon: Icon
}: StatCardProps) {
  
  const isPositive = trend === undefined || trend >= 0;

  return (
    <motion.div 
      whileHover={{ y: -2 }}
      className="bg-[#0F0F0F] rounded-lg p-5 flex items-center gap-5 border border-[#1F1F1F] hover:border-[#333] transition-colors"
    >
      <div className={`w-12 h-12 rounded bg-[#161616] flex items-center justify-center shrink-0 border border-[#1F1F1F] ${isPositive ? 'text-[#00FF9D]' : 'text-[#FF3B30]'}`}>
        {Icon ? <Icon size={20} /> : (isPositive ? <TrendingUp size={20} /> : <TrendingDown size={20} />)}
      </div>
      
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-black text-[#444444] uppercase tracking-[0.2em] mb-1">{title}</p>
        <div className="flex items-baseline gap-2">
           <h3 className="text-xl font-bold text-white font-mono tracking-tighter truncate">
             {prefix}{value.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}{suffix}
           </h3>
           {trend !== undefined && (
             <span className={`text-[10px] font-black font-mono ${trend >= 0 ? 'text-[#00FF9D]' : 'text-[#FF3B30]'}`}>
               {trend >= 0 ? '+' : ''}{trend.toFixed(2)}%
             </span>
           )}
        </div>
      </div>
    </motion.div>
  );
}
