import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { 
  LayoutDashboard, BarChart3, Receipt, Settings, 
  Activity, Zap, Shield, Cpu, Clock, Terminal
} from "lucide-react";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "QuantAI | Professional Trading Terminal",
  description: "High-frequency algorithmic trading workstation",
};

const navItems = [
  { href: "/",        icon: LayoutDashboard, label: "Overview" },
  { href: "/charts",  icon: BarChart3,       label: "Terminal" },
  { href: "/trades",  icon: Receipt,         label: "Order Logs" },
  { href: "/settings",icon: Settings,        label: "Configuration" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="bg-[var(--bg-base)] text-[var(--text-primary)] selection:bg-[#39D353]/30">
        <div className="flex min-h-screen">

          {/* ── Wide Carbon Sidebar ── */}
          <aside className="w-[300px] bg-[var(--bg-surface)] border-r border-[var(--border)] flex flex-col shrink-0">
            {/* Header */}
            <div className="p-8 border-b border-[var(--border)]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-[#39D353]/10 flex items-center justify-center border border-[#39D353]/20">
                  <Terminal size={18} className="text-[#39D353]" />
                </div>
                <h1 className="text-xl font-black tracking-tighter uppercase italic text-[var(--text-primary)]">QuantAI<span className="text-[#39D353]">.</span></h1>
              </div>
            </div>

            {/* Navigation (Roomy) */}
            <nav className="flex-1 p-6 space-y-1">
              <p className="px-4 text-[10px] font-black text-[var(--text-muted)] uppercase tracking-[0.2em] mb-4">Operations</p>
              {navItems.map(({ href, icon: Icon, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="flex items-center gap-4 px-4 py-3.5 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)] transition-all font-bold text-sm group"
                >
                  <Icon size={18} className="group-hover:text-[#39D353]" />
                  <span>{label}</span>
                </Link>
              ))}
            </nav>

            {/* Performance Stats Footer */}
            <div className="p-8 border-t border-[var(--border)] bg-[var(--bg-base)]">
              <div className="space-y-4">
                 <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-[var(--text-muted)]">
                    <span>Engine Health</span>
                    <span className="text-[#39D353]">100%</span>
                 </div>
                 <div className="h-1 bg-[var(--border)] rounded-full overflow-hidden">
                    <div className="h-full w-full bg-[#39D353] shadow-[0_0_10px_rgba(57,211,83,0.3)]" />
                 </div>
                 <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-[#39D353] animate-pulse" />
                    <span className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest">Bot Streaming Live</span>
                 </div>
              </div>
            </div>
          </aside>

          {/* ── Main Workspace ── */}
          <div className="flex-1 flex flex-col min-w-0">
            
            {/* Functional Header (No Fluff) */}
            <header className="h-16 flex items-center justify-between px-8 bg-[var(--bg-base)] border-b border-[var(--border)]">
               <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--text-secondary)]">
                     <Clock size={14} />
                     <span suppressHydrationWarning>{new Date().toLocaleTimeString()} UTC</span>
                  </div>
                  <div className="w-px h-4 bg-[var(--border)]" />
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--text-secondary)]">
                     <Activity size={14} />
                     <span>Latency: <span className="text-[#39D353]">14ms</span></span>
                  </div>
               </div>

               <div className="flex items-center gap-6">
                  <div className="flex items-center gap-4 px-4 py-2 bg-[var(--bg-surface)] rounded border border-[var(--border)]">
                     <div className="flex flex-col items-end">
                        <span className="text-[9px] font-black text-[var(--text-muted)] uppercase tracking-widest">Active Threads</span>
                        <span className="text-xs font-bold text-[var(--text-primary)] font-mono">128 INSTANCE</span>
                     </div>
                     <Cpu size={16} className="text-[var(--text-secondary)]" />
                  </div>
                  <div className="w-8 h-8 rounded-full bg-[var(--bg-elevated)] border border-[var(--border)] flex items-center justify-center text-[var(--text-secondary)]">
                    <Shield size={16} />
                  </div>
               </div>
            </header>

            {/* Content Area */}
            <main className="flex-1 p-8 overflow-y-auto">
              <div className="max-w-[1440px] mx-auto">
                {children}
              </div>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
