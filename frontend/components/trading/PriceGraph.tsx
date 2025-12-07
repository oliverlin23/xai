"use client"

import { useEffect, useState, useMemo } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import { supabase } from "@/lib/supabase"

interface PriceDataPoint {
  time: string
  price: number
  timestamp: number
}

interface PriceGraphProps {
  sessionId: string | null
}

interface TraderPosition {
  name: string
  trader_type: string
  position: number
  cash: number
  pnl: number
}

interface RecentOrder {
  id: string
  trader_name: string
  side: "buy" | "sell"
  price: number
  quantity: number
  filled_quantity: number
  status: string
  created_at: string
}

interface RecentTrade {
  id: string
  buyer_name: string
  seller_name: string
  price: number
  quantity: number
  created_at: string
}

export function PriceGraph({ sessionId }: PriceGraphProps) {
  const [priceHistory, setPriceHistory] = useState<PriceDataPoint[]>([])
  const [currentPrice, setCurrentPrice] = useState<number | null>(null)
  const [priceChange, setPriceChange] = useState<number>(0)
  const [bestBid, setBestBid] = useState<number | null>(null)
  const [bestAsk, setBestAsk] = useState<number | null>(null)
  const [traderPositions, setTraderPositions] = useState<TraderPosition[]>([])
  const [recentOrders, setRecentOrders] = useState<RecentOrder[]>([])
  const [recentTrades, setRecentTrades] = useState<RecentTrade[]>([])

  // Fetch initial trades and calculate price history
  useEffect(() => {
    if (!sessionId) return

    const fetchInitialData = async () => {
      try {
        const { data: trades, error: tradesError } = await supabase
          .from("trades")
          .select("price, created_at")
          .eq("session_id", sessionId)
          .order("created_at", { ascending: true })
          .limit(100)

        if (tradesError) {
          console.error("Error fetching trades:", tradesError)
          return
        }

        if (trades && trades.length > 0) {
          const tradeData = trades as Array<{ price: number; created_at: string }>
          const history: PriceDataPoint[] = tradeData.map((trade) => ({
            time: new Date(trade.created_at).toLocaleTimeString(),
            price: trade.price,
            timestamp: new Date(trade.created_at).getTime(),
          }))
          setPriceHistory(history)
          setCurrentPrice(tradeData[tradeData.length - 1].price)
          if (tradeData.length > 1) {
            setPriceChange(tradeData[tradeData.length - 1].price - tradeData[0].price)
          }
        }

        const { data: bids } = await supabase
          .from("orderbook_live")
          .select("price")
          .eq("session_id", sessionId)
          .eq("side", "buy")
          .in("status", ["open", "partially_filled"])
          .order("price", { ascending: false })
          .limit(1)

        const { data: asks } = await supabase
          .from("orderbook_live")
          .select("price")
          .eq("session_id", sessionId)
          .eq("side", "sell")
          .in("status", ["open", "partially_filled"])
          .order("price", { ascending: true })
          .limit(1)

        const bidData = bids as Array<{ price: number }> | null
        const askData = asks as Array<{ price: number }> | null

        if (bidData && bidData.length > 0) {
          setBestBid(bidData[0].price)
        }
        if (askData && askData.length > 0) {
          setBestAsk(askData[0].price)
        }

        if (bidData && bidData.length > 0 && askData && askData.length > 0) {
          const midpoint = Math.round((bidData[0].price + askData[0].price) / 2)
          if (!currentPrice) {
            setCurrentPrice(midpoint)
          }
        }

        const { data: positions } = await supabase
          .from("trader_state_live")
          .select("name, trader_type, position, cash, pnl")
          .eq("session_id", sessionId)
          .order("position", { ascending: false })

        if (positions) {
          setTraderPositions(positions as TraderPosition[])
        }

        const { data: orders } = await supabase
          .from("orderbook_live")
          .select("id, trader_name, side, price, quantity, filled_quantity, status, created_at")
          .eq("session_id", sessionId)
          .order("created_at", { ascending: false })
          .limit(20)

        if (orders) {
          setRecentOrders(orders as RecentOrder[])
        }

        const { data: recentTradesData } = await supabase
          .from("trades")
          .select("id, buyer_name, seller_name, price, quantity, created_at")
          .eq("session_id", sessionId)
          .order("created_at", { ascending: false })
          .limit(20)

        if (recentTradesData) {
          setRecentTrades(recentTradesData as RecentTrade[])
        }
      } catch (error) {
        console.error("Error fetching initial data:", error)
      }
    }

    fetchInitialData()
  }, [sessionId, currentPrice])

  // Subscribe to real-time trades
  useEffect(() => {
    if (!sessionId) return

    const channel = supabase
      .channel(`trades:${sessionId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "trades",
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => {
          const newTrade = payload.new as any
          const newPrice = newTrade.price
          const tradeTime = new Date(newTrade.created_at)

          setPriceHistory((prev) => {
            const updated = [
              ...prev,
              {
                time: tradeTime.toLocaleTimeString(),
                price: newPrice,
                timestamp: tradeTime.getTime(),
              },
            ]
            return updated.slice(-100)
          })

          setCurrentPrice(newPrice)
          if (priceHistory.length > 0) {
            setPriceChange(newPrice - priceHistory[priceHistory.length - 1].price)
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [sessionId, priceHistory])

  // Subscribe to real-time orderbook changes
  useEffect(() => {
    if (!sessionId) return

    const updateOrderbook = async () => {
      const { data: bids } = await supabase
        .from("orderbook_live")
        .select("price")
        .eq("session_id", sessionId)
        .eq("side", "buy")
        .in("status", ["open", "partially_filled"])
        .order("price", { ascending: false })
        .limit(1)

      const { data: asks } = await supabase
        .from("orderbook_live")
        .select("price")
        .eq("session_id", sessionId)
        .eq("side", "sell")
        .in("status", ["open", "partially_filled"])
        .order("price", { ascending: true })
        .limit(1)

      const bidData = bids as Array<{ price: number }> | null
      const askData = asks as Array<{ price: number }> | null

      if (bidData && bidData.length > 0) {
        setBestBid(bidData[0].price)
      } else {
        setBestBid(null)
      }

      if (askData && askData.length > 0) {
        setBestAsk(askData[0].price)
      } else {
        setBestAsk(null)
      }

      if (bidData && bidData.length > 0 && askData && askData.length > 0 && !currentPrice) {
        const midpoint = Math.round((bidData[0].price + askData[0].price) / 2)
        setCurrentPrice(midpoint)
      }

      const { data: orders } = await supabase
        .from("orderbook_live")
        .select("id, trader_name, side, price, quantity, filled_quantity, status, created_at")
        .eq("session_id", sessionId)
        .order("created_at", { ascending: false })
        .limit(20)

      if (orders) {
        setRecentOrders(orders as RecentOrder[])
      }
    }

    const channel = supabase
      .channel(`orderbook:${sessionId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "orderbook_live",
          filter: `session_id=eq.${sessionId}`,
        },
        () => updateOrderbook()
      )
      .subscribe()

    const traderChannel = supabase
      .channel(`trader_state:${sessionId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "trader_state_live",
          filter: `session_id=eq.${sessionId}`,
        },
        async () => {
          const { data: positions } = await supabase
            .from("trader_state_live")
            .select("name, trader_type, position, cash, pnl")
            .eq("session_id", sessionId)
            .order("position", { ascending: false })

          if (positions) {
            setTraderPositions(positions as TraderPosition[])
          }
        }
      )
      .subscribe()

    updateOrderbook()
    const interval = setInterval(updateOrderbook, 2000)

    return () => {
      supabase.removeChannel(channel)
      supabase.removeChannel(traderChannel)
      clearInterval(interval)
    }
  }, [sessionId, currentPrice])

  // Calculate display price (use last trade or midpoint)
  const displayPrice = useMemo(() => {
    if (currentPrice !== null) return currentPrice
    if (bestBid !== null && bestAsk !== null) {
      return Math.round((bestBid + bestAsk) / 2)
    }
    return null
  }, [currentPrice, bestBid, bestAsk])

  const priceColor = priceChange >= 0 ? "text-emerald-400" : "text-red-400"

  // Generate mock data when no session
  const mockData: PriceDataPoint[] = useMemo(() => {
    if (sessionId) return []

    const now = Date.now()
    const basePrice = 45
    const data: PriceDataPoint[] = []

    for (let i = 50; i >= 0; i--) {
      const timestamp = now - i * 6000
      const time = new Date(timestamp)
      const priceChange = (Math.random() - 0.5) * 2
      const price = Math.max(20, Math.min(80, basePrice + priceChange * i * 0.1))

      data.push({
        time: time.toLocaleTimeString(),
        price: Math.round(price),
        timestamp,
      })
    }

    return data
  }, [sessionId])

  // Use mock data when no session
  useEffect(() => {
    if (!sessionId && mockData.length > 0) {
      setPriceHistory(mockData)
      setCurrentPrice(mockData[mockData.length - 1].price)
      setPriceChange(mockData[mockData.length - 1].price - mockData[0].price)
      setBestBid(mockData[mockData.length - 1].price - 2)
      setBestAsk(mockData[mockData.length - 1].price + 2)

      const interval = setInterval(() => {
        setPriceHistory((prev) => {
          if (prev.length === 0) return prev
          const lastPrice = prev[prev.length - 1].price
          const priceChange = (Math.random() - 0.5) * 2
          const newPrice = Math.max(20, Math.min(80, lastPrice + priceChange))
          const newTime = new Date()

          const updated = [
            ...prev,
            {
              time: newTime.toLocaleTimeString(),
              price: Math.round(newPrice),
              timestamp: newTime.getTime(),
            },
          ]

          setCurrentPrice(Math.round(newPrice))
          setPriceChange(Math.round(newPrice) - prev[0].price)
          setBestBid(Math.round(newPrice) - 2)
          setBestAsk(Math.round(newPrice) + 2)

          return updated.slice(-100)
        })
      }, 3000)

      return () => clearInterval(interval)
    }
  }, [sessionId, mockData])

  return (
    <div className="w-full h-full flex flex-col text-[#f7f5f0]">
      {/* Header with current price */}
      <div className="mb-3">
        <div className="text-sm text-gray-400 mb-2">Market Price</div>
        <div className="flex items-baseline gap-3">
          {displayPrice !== null ? (
            <>
              <span className={`text-4xl font-bold ${priceColor}`}>{displayPrice}¢</span>
              {priceChange !== 0 && (
                <span className={`text-lg ${priceColor}`}>
                  {priceChange > 0 ? "+" : ""}
                  {priceChange}¢
                </span>
              )}
            </>
          ) : (
            <span className="text-2xl text-gray-500">--</span>
          )}
        </div>
        {(bestBid !== null || bestAsk !== null) && (
          <div className="text-xs text-gray-500 mt-2">
            Bid: {bestBid ?? "--"}¢ | Ask: {bestAsk ?? "--"}¢
          </div>
        )}
      </div>

      {/* Price Chart */}
      <div className="h-48 min-h-[180px]">
        {priceHistory.length > 0 || (!sessionId && mockData.length > 0) ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sessionId ? priceHistory : priceHistory.length > 0 ? priceHistory : mockData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#9ca3af" tick={{ fill: "#9ca3af", fontSize: 12 }} />
              <YAxis
                domain={["dataMin - 2", "dataMax + 2"]}
                stroke="#9ca3af"
                tick={{ fill: "#9ca3af", fontSize: 12 }}
                label={{ value: "Price (¢)", angle: -90, position: "insideLeft", fill: "#9ca3af" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  color: "#f7f5f0",
                }}
                labelStyle={{ color: "#9ca3af" }}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke={priceChange >= 0 ? "#34d399" : "#f87171"}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: priceChange >= 0 ? "#34d399" : "#f87171" }}
              />
              {displayPrice !== null && (
                <ReferenceLine
                  y={displayPrice}
                  stroke="#6366f1"
                  strokeDasharray="2 2"
                  label={{ value: "Current", position: "right", fill: "#6366f1" }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-500">
            {!sessionId ? (
              <div className="text-center">
                <div className="text-lg mb-2">Demo Mode</div>
                <div className="text-sm">Showing mock market data</div>
              </div>
            ) : bestBid !== null || bestAsk !== null ? (
              <div className="text-center">
                <div className="text-lg mb-2">Waiting for trades...</div>
                <div className="text-sm">
                  Market: {bestBid ?? "--"}¢ / {bestAsk ?? "--"}¢
                </div>
              </div>
            ) : (
              <div>No market data available</div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Panels: Contracts (left) and Orders/Trades (right) */}
      <div className="grid grid-cols-2 gap-4 mt-3 h-86 mb-0">
        <div className="border border-[#2d3748] rounded-lg px-4 pt-4 pb-2 bg-[#0f172a]/50 overflow-hidden flex flex-col">
          <div className="text-sm font-semibold mb-3 text-gray-300">Contracts (Positions)</div>
          <div className="flex-1 overflow-y-auto space-y-2">
            {sessionId ? (
              traderPositions.length > 0 ? (
                traderPositions.map((trader, idx) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center text-xs bg-[#1a1f2e]/50 rounded px-2 py-1.5 border border-[#2d3748]"
                  >
                    <div className="flex flex-col">
                      <span className="font-semibold text-gray-200">{trader.name}</span>
                      <span className="text-gray-400 text-[10px]">{trader.trader_type}</span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className={trader.position >= 0 ? "text-emerald-400" : "text-red-400"}>
                        {trader.position > 0 ? "+" : ""}
                        {trader.position}
                      </span>
                      <span className="text-gray-500 text-[10px]">
                        ${trader.cash.toFixed(2)} | {trader.pnl >= 0 ? "+" : ""}
                        {trader.pnl.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 text-sm py-8">No positions yet</div>
              )
            ) : (
              <div className="space-y-2">
                {["conservative", "momentum", "balanced", "realtime", "historical"].map((name, idx) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center text-xs bg-[#1a1f2e]/50 rounded px-2 py-1.5 border border-[#2d3748]"
                  >
                    <div className="flex flex-col">
                      <span className="font-semibold text-gray-200">{name}</span>
                      <span className="text-gray-400 text-[10px]">fundamental</span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className={idx % 2 === 0 ? "text-emerald-400" : "text-red-400"}>
                        {idx % 2 === 0 ? "+" : ""}
                        {Math.floor(Math.random() * 200) - 100}
                      </span>
                      <span className="text-gray-500 text-[10px]">
                        ${(1000 + (Math.random() * 200 - 100)).toFixed(2)} | {idx % 2 === 0 ? "+" : ""}
                        {(Math.random() * 50).toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="border border-[#2d3748] rounded-lg px-4 pt-4 pb-2 bg-[#0f172a]/50 overflow-hidden flex flex-col">
          <div className="text-sm font-semibold mb-3 text-gray-300">Recent Orders & Trades</div>
          <div className="flex-1 overflow-y-auto space-y-2">
            {sessionId ? (
              <>
                {recentTrades.slice(0, 5).map((trade, idx) => (
                  <div
                    key={trade.id || idx}
                    className="text-xs bg-emerald-900/20 rounded px-2 py-1.5 border border-emerald-500/30"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-emerald-300 font-semibold">
                        {trade.buyer_name} → {trade.seller_name}
                      </span>
                      <span className="text-emerald-200">{trade.price}¢</span>
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>Qty: {trade.quantity}</span>
                      <span>{new Date(trade.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
                {recentOrders.slice(0, 5).map((order, idx) => (
                  <div
                    key={order.id || idx}
                    className={`text-xs rounded px-2 py-1.5 border ${
                      order.side === "buy"
                        ? "bg-emerald-900/20 border-emerald-500/30"
                        : "bg-red-900/20 border-red-500/30"
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span
                        className={`font-semibold ${
                          order.side === "buy" ? "text-emerald-300" : "text-red-300"
                        }`}
                      >
                        {order.trader_name} {order.side === "buy" ? "BUY" : "SELL"}
                      </span>
                      <span className={order.side === "buy" ? "text-emerald-200" : "text-red-200"}>
                        {order.price}¢
                      </span>
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>
                        {order.filled_quantity}/{order.quantity} {order.status}
                      </span>
                      <span>{new Date(order.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
                {recentTrades.length === 0 && recentOrders.length === 0 && (
                  <div className="text-center text-gray-500 text-sm py-8">No orders or trades yet</div>
                )}
              </>
            ) : (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, idx) => (
                  <div
                    key={idx}
                    className={`text-xs rounded px-2 py-1.5 border ${
                      idx % 2 === 0
                        ? "bg-emerald-900/20 border-emerald-500/30"
                        : "bg-red-900/20 border-red-500/30"
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span
                        className={`font-semibold ${idx % 2 === 0 ? "text-emerald-300" : "text-red-300"}`}
                      >
                        {idx % 2 === 0 ? "conservative BUY" : "momentum SELL"}
                      </span>
                      <span className={idx % 2 === 0 ? "text-emerald-200" : "text-red-200"}>
                        {40 + Math.floor(Math.random() * 20)}¢
                      </span>
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>{idx % 2 === 0 ? "100/100 filled" : "50/100 open"}</span>
                      <span>{new Date(Date.now() - idx * 10000).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

