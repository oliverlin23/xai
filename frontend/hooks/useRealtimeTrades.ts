"use client"

import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"

export interface Trade {
  id: string
  session_id: string
  buyer_name: string
  seller_name: string
  price: number
  quantity: number
  created_at: string
}

export interface OrderBookLevel {
  price: number
  quantity: number
  order_count: number
}

export interface OrderBook {
  bids: OrderBookLevel[]
  asks: OrderBookLevel[]
  last_price: number | null
  spread: number | null
  volume: number
}

export interface TraderState {
  id: string
  session_id: string
  trader_type: string
  name: string
  system_prompt: string | null
  position: number
  cash: number
  pnl: number
  updated_at: string
}

interface RealtimeTradingData {
  trades: Trade[]
  traderStates: TraderState[]
  lastTrade: Trade | null
}

/**
 * Hook to subscribe to real-time trading updates for a session.
 * Subscribes to: trades, trader_state_live tables
 */
export function useRealtimeTrades(sessionId: string) {
  const [data, setData] = useState<RealtimeTradingData>({
    trades: [],
    traderStates: [],
    lastTrade: null,
  })

  useEffect(() => {
    if (!sessionId) return

    const channel = supabase
      .channel(`trading:${sessionId}`)
      // Subscribe to new trades
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "trades",
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => {
          const newTrade = payload.new as Trade
          setData((prev) => ({
            ...prev,
            trades: [...prev.trades, newTrade],
            lastTrade: newTrade,
          }))
        }
      )
      // Subscribe to trader state updates
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "trader_state_live",
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => {
          const newTrader = payload.new as TraderState
          setData((prev) => ({
            ...prev,
            traderStates: [...prev.traderStates.filter(t => t.id !== newTrader.id), newTrader],
          }))
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "trader_state_live",
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => {
          const updatedTrader = payload.new as TraderState
          setData((prev) => ({
            ...prev,
            traderStates: prev.traderStates.map((t) =>
              t.id === updatedTrader.id ? updatedTrader : t
            ),
          }))
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [sessionId])

  return data
}
