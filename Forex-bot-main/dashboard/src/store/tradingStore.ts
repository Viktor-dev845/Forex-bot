import { create } from 'zustand';

// ── Types matching bot_status.json exactly ──────────────────────────────────

export interface PositionInfo {
  qty: number;
  side: 'long' | 'short';
  sl_price?: number;
  tp_price?: number;
}

export interface TradeRecord {
  timestamp: string;
  symbol: string;
  side: 'BUY' | 'SELL' | 'CLOSE';
  quantity: number;
  price: number;
  order_id?: string;
  pnl?: number;
  notes?: string;
}

export interface PredictionInfo {
  prob: number;
  signal: 'UP' | 'DOWN' | 'NEUTRAL';
  timestamp: string;
  ensemble?: Record<string, number>;
}

export interface BotState {
  timestamp?: string;
  market_type: string;
  symbols: string[];
  account: {
    cash: number;
    equity: number;
    return_pct?: number;
    buying_power?: number;
    daily_pnl: number;
    initial_capital?: number;
  };
  positions: Record<string, PositionInfo | null>;
  entry_prices?: Record<string, number>;
  predictions: Record<string, PredictionInfo>;
  trade_history?: TradeRecord[];
  sl_cooldown?: Record<string, number>;
  latest_logs?: string[];
  is_running?: boolean;
}

export interface TickData {
  [symbol: string]: {
    time: number;
    price: number;
  };
}

interface TradingStore {
  botState: BotState | null;
  ticks: TickData;
  isConnected: boolean;
  setBotState: (state: BotState) => void;
  updateTicks: (ticks: TickData) => void;
  setConnected: (status: boolean) => void;
}

export const useTradingStore = create<TradingStore>((set) => ({
  botState: null,
  ticks: {},
  isConnected: false,

  setBotState: (state) => set({ botState: state }),

  updateTicks: (newTicks) => set((prev) => ({
    ticks: { ...prev.ticks, ...newTicks }
  })),

  setConnected: (status) => set({ isConnected: status }),
}));
