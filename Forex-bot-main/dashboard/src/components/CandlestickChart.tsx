"use client";

import {
  createChart,
  ColorType,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickSeriesOptions,
} from 'lightweight-charts';
import { useEffect, useRef } from 'react';
import { useTradingStore } from '../store/tradingStore';

interface ChartProps {
  symbol: string;
  timeframe?: string;
}

interface LiveCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export function CandlestickChart({ symbol, timeframe = "M5" }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lastUpdateRef = useRef<number>(0);
  // Track the current live candle locally — avoids relying on series.data()
  const currentCandleRef = useRef<LiveCandle | null>(null);

  const ticks = useTradingStore(state => state.ticks);
  const activeTick = ticks[symbol];

  // 1. Initialize Chart & Load History
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const containerEl = chartContainerRef.current;

    const chart = createChart(containerEl, {
      width: containerEl.clientWidth,
      height: containerEl.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: 'rgba(148, 163, 184, 0.4)', style: 3 },
        horzLine: { color: 'rgba(148, 163, 184, 0.4)', style: 3 },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        autoScale: true,
      },
    });

    // v5 API: chart.addSeries(CandlestickSeries, options)
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    } as Partial<CandlestickSeriesOptions>);

    chartRef.current = chart;
    seriesRef.current = series;
    currentCandleRef.current = null;

    // Fetch history
    const fetchHistory = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/candles/${encodeURIComponent(symbol)}/${timeframe}`);
        const data = await res.json();

        if (Array.isArray(data) && data.length > 0) {
          // Deduplicate and sort ascending
          const seen = new Set<number>();
          const uniqueData = data.filter((v: any) => {
            if (seen.has(v.time)) return false;
            seen.add(v.time);
            return true;
          });
          uniqueData.sort((a: any, b: any) => a.time - b.time);

          series.setData(uniqueData);
          const lastCandle = uniqueData[uniqueData.length - 1];
          lastUpdateRef.current = lastCandle.time;
          currentCandleRef.current = lastCandle;

          chart.timeScale().fitContent();
        }
      } catch (err) {
        console.error("Failed to fetch historical candles:", err);
      }
    };

    fetchHistory();

    // ResizeObserver — sole controller of chart dimensions
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length === 0 || entries[0].target !== containerEl) return;
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        chart.applyOptions({ width, height });
      }
    });

    resizeObserver.observe(containerEl);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      currentCandleRef.current = null;
    };
  }, [symbol, timeframe]);

  // 2. Stream Live Ticks
  useEffect(() => {
    if (!seriesRef.current || !activeTick) return;

    const getSeconds = (tf: string) => {
      if (tf === "M1") return 60;
      if (tf === "M5") return 300;
      if (tf === "M15") return 900;
      if (tf === "H1") return 3600;
      return 300;
    };

    const interval = getSeconds(timeframe);
    const candleTime = Math.floor(activeTick.time / interval) * interval;

    try {
      if (candleTime > lastUpdateRef.current) {
        // New candle
        const newCandle: LiveCandle = {
          time: candleTime,
          open: activeTick.price,
          high: activeTick.price,
          low: activeTick.price,
          close: activeTick.price,
        };
        seriesRef.current.update(newCandle as any);
        lastUpdateRef.current = candleTime;
        currentCandleRef.current = newCandle;
      } else if (currentCandleRef.current && currentCandleRef.current.time === candleTime) {
        // Update current candle via tracked ref
        const updated: LiveCandle = {
          time: candleTime,
          open: currentCandleRef.current.open,
          high: Math.max(currentCandleRef.current.high, activeTick.price),
          low: Math.min(currentCandleRef.current.low, activeTick.price),
          close: activeTick.price,
        };
        seriesRef.current.update(updated as any);
        currentCandleRef.current = updated;
      }
    } catch (err) {
      console.warn("Chart update error:", err);
    }
  }, [activeTick, timeframe]);

  return (
    <div className="w-full h-full relative">
      <div
        ref={chartContainerRef}
        className="absolute inset-0"
      />
    </div>
  );
}
