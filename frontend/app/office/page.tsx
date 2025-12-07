"use client"

import { useEffect, useState, Suspense, useRef } from "react"
import { useTradingStore } from "@/lib/store"
import { useSearchParams } from "next/navigation"
import Image from "next/image"
import { api } from "@/lib/api"
import { useRealtimeTrades, Trade, TraderState } from "@/hooks/useRealtimeTrades"
import { Press_Start_2P } from "next/font/google"
import { PriceGraph } from "@/components/trading/PriceGraph"
import { supabase } from "@/lib/supabase"

const pressStart = Press_Start_2P({ weight: "400", subsets: ["latin"] })

const workerSprites = [
  "/sprites/worker1.png",
  "/sprites/worker2.png",
  "/sprites/worker4.png",
  "/sprites/worker1.png",
  "/sprites/worker4.png",
  "/sprites/worker2.png",
  "/sprites/worker1.png",
  "/sprites/worker2.png",
]

// All 18 agents in order
const AGENT_CONFIG = {
  // 5 Fundamental Traders
  fundamental: {
    conservative: { name: "Conservative", role: "Fundamental", description: "Risk-averse, anchors to base rates" },
    momentum: { name: "Momentum", role: "Fundamental", description: "Follows market trends and price action" },
    historical: { name: "Historical", role: "Fundamental", description: "Relies on precedent and base rates" },
    balanced: { name: "Balanced", role: "Fundamental", description: "Weighs multiple perspectives equally" },
    realtime: { name: "Realtime", role: "Fundamental", description: "Highly responsive to new information" },
  },
  // 9 Noise Traders (X spheres)
  noise: {
    eacc_sovereign: { name: "e/acc Sovereign", role: "Noise", description: "Tech accelerationism sphere" },
    america_first: { name: "America First", role: "Noise", description: "Conservative populist sphere" },
    blue_establishment: { name: "Blue Establishment", role: "Noise", description: "Democratic establishment sphere" },
    progressive_left: { name: "Progressive Left", role: "Noise", description: "Progressive activism sphere" },
    optimizer_idw: { name: "Optimizer IDW", role: "Noise", description: "Intellectual dark web sphere" },
    fintwit_market: { name: "FinTwit Market", role: "Noise", description: "Financial Twitter sphere" },
    builder_engineering: { name: "Builder Engineering", role: "Noise", description: "Engineering & builder sphere" },
    academic_research: { name: "Academic Research", role: "Noise", description: "Academic and research sphere" },
    osint_intel: { name: "OSINT Intel", role: "Noise", description: "Open source intelligence sphere" },
  },
  // 4 User Agents
  user: {
    oliver: { name: "Oliver", role: "User", description: "Tracks Oliver's X account" },
    owen: { name: "Owen", role: "User", description: "Tracks Owen's X account" },
    skylar: { name: "Skylar", role: "User", description: "Tracks Skylar's X account" },
    tyler: { name: "Tyler", role: "User", description: "Tracks Tyler's X account" },
  },
}

// Flatten to ordered list
const ALL_AGENTS = [
  ...Object.entries(AGENT_CONFIG.fundamental).map(([key, val]) => ({ key, ...val, type: "fundamental" })),
  ...Object.entries(AGENT_CONFIG.noise).map(([key, val]) => ({ key, ...val, type: "noise" })),
  ...Object.entries(AGENT_CONFIG.user).map(([key, val]) => ({ key, ...val, type: "user" })),
]

const statusStyles = {
  idle: { label: "Active", className: "bg-yellow-400 shadow-[0_0_10px_rgba(234,179,8,0.45)]" },
  analyzing: { label: "Processing", className: "bg-yellow-400 shadow-[0_0_10px_rgba(234,179,8,0.45)]" },
  "submitting-order": { label: "Submitting", className: "bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.45)]" },
  offline: { label: "Offline", className: "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.45)]" },
  buy: { label: "Buy", className: "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.45)]" },
  sell: { label: "Sell", className: "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.45)]" },
}

const PartitionFrame = () => (
  <>
    <img
      src="/sprites/office-partitions-1.png"
      className="absolute -top-6 left-0 w-full h-full object-contain pixelated opacity-80 pointer-events-none z-10"
      alt="partition top"
    />
    <img
      src="/sprites/office-partitions-2.png"
      className="absolute -top-6 right-1/2 w-full h-full object-contain pixelated opacity-80 pointer-events-none z-10"
      alt="partition left"
    />
  </>
)

const Cubicle = ({
  sprite,
  name,
  role,
  status,
  flashStatus,
  description,
  prediction,
  onClick,
  hasPlant = false,
  hasTrash = false,
}: {
  sprite: string
  name: string
  role: string
  status: keyof typeof statusStyles
  flashStatus?: "buy" | "sell" | null
  description?: string
  prediction?: number
  onClick?: () => void
  hasPlant?: boolean
  hasTrash?: boolean
}) => {
  // Use flash status if present, otherwise use regular status
  const displayStatus = flashStatus || status
  const statusMeta = statusStyles[displayStatus]

  return (
    <div className="relative w-[180px] h-[180px]">
      <PartitionFrame />

      {/* Clickable area */}
      <div 
        className="absolute inset-4 group cursor-pointer"
        onClick={onClick}
      >
        {/* Hover card */}
        <div className="pointer-events-none absolute -top-2 left-1/2 -translate-x-1/2 -translate-y-full z-40 px-3 py-2 rounded-md bg-slate-900/90 border border-white/10 shadow-lg text-xs text-slate-100 opacity-0 transition-opacity duration-150 group-hover:opacity-100 max-w-xs">
          <div className="font-semibold mb-1">{name}</div>
          <div className="text-[11px] text-slate-300 mb-1">Role: {role}</div>
          {description && (
            <div className="text-[10px] text-slate-400 mt-2 mb-2 leading-relaxed whitespace-normal max-w-[200px]">
              {description}
            </div>
          )}
          {prediction !== undefined && (
            <div className="mt-2 pt-2 border-t border-white/10">
              <div className="text-[10px] text-emerald-300">
                Last Prediction: {prediction}¢
              </div>
            </div>
          )}
        </div>

        {/* Worker */}
        <img
          src={sprite}
          className="absolute top-4 left-1/2 -translate-x-1/2 w-[76px] h-[76px] object-contain pixelated z-20 drop-shadow-[0_10px_12px_rgba(0,0,0,0.25)] transition-transform group-hover:-translate-y-1 group-hover:scale-105"
          alt={name}
        />

        {/* Optional decor */}
        {hasPlant && (
          <img
            src="/sprites/plant.png"
            className="absolute bottom-3 right-2 w-10 h-10 object-contain pixelated z-10 opacity-90"
            alt="plant"
          />
        )}
        {hasTrash && (
          <img
            src="/sprites/Trash.png"
            className="absolute bottom-3 left-2 w-10 h-10 object-contain pixelated z-10 opacity-80"
            alt="trash"
          />
        )}

        {/* Status dot */}
        <div className="absolute top-1 left-1 z-30 flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${statusMeta.className}`} title={statusMeta.label} />
        </div>
      </div>
    </div>
  )
}

interface AgentInfo {
  key: string
  name: string
  role: string
  type: string
  description: string
  status: "idle" | "analyzing" | "offline"
  prediction?: number
  traderState?: TraderState
}

const OfficeScene = ({ 
  forecasterResponses, 
  onForecasterClick,
  traderFlashStates
}: { 
  forecasterResponses: ForecasterResponse[]
  onForecasterClick: (response: ForecasterResponse) => void
  traderFlashStates: Record<string, "buy" | "sell" | null>
}) => {
  return (
    <div className="relative w-full h-full flex items-center justify-center p-0">
      <div className="relative z-10 w-full h-full flex flex-col justify-between">
        {/* Main Office Floor */}
        <div className="flex-1 flex items-center justify-center gap-52 px-6 pt-48">
          {/* Left Bank - First 9 agents */}
          <div className="grid grid-cols-3 gap-x-0 gap-y-0">
            {agents.slice(0, 9).map((agent, i) => (
              <div key={agent.key} className="flex justify-center">
                <Cubicle
                  sprite={workerSprites[i % workerSprites.length]}
                  name={agent.name}
                  role={agent.role}
                  status={agent.status}
                  flashStatus={traderFlashStates[agent.name] || null}
                  description={agent.description}
                  probability={agent.probability}
                  confidence={agent.confidence}
                  onClick={agent.response ? () => agent.response && onForecasterClick(agent.response) : undefined}
                  hasPlant={false}
                  hasTrash={i % 4 === 1}
                />
              </div>
            ))}
          </div>

          {/* Right Bank - Next 9 agents */}
          <div className="grid grid-cols-3 gap-x-0 gap-y-0">
            {agents.slice(9, 18).map((agent, i) => {
              const idx = i + 9
              return (
                <div key={agent.key} className="flex justify-center">
                  <Cubicle
                    sprite={workerSprites[idx % workerSprites.length]}
                    name={agent.name}
                    role={agent.role}
                    status={agent.status}
                    flashStatus={traderFlashStates[agent.name] || null}
                    description={agent.description}
                    probability={agent.probability}
                    confidence={agent.confidence}
                    onClick={agent.response ? () => agent.response && onForecasterClick(agent.response) : undefined}
                    hasPlant={false}
                    hasTrash={idx % 4 === 1}
                  />
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

const TradeFeed = ({ trades }: { trades: Trade[] }) => {
  const recentTrades = trades.slice(-20).reverse()
  
  return (
    <div className="absolute top-4 right-4 w-72 max-h-[400px] overflow-hidden rounded-lg border-2 border-[#2d3748] bg-[#0f172a]/95 text-[#f7f5f0] shadow-lg z-40">
      <div className="px-3 py-2 border-b border-[#2d3748] bg-[#1a1f2e]">
        <div className="text-sm font-semibold tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          Live Trade Feed
        </div>
      </div>
      <div className="overflow-y-auto max-h-[350px]">
        {recentTrades.length === 0 ? (
          <div className="px-3 py-4 text-center text-slate-500 text-xs">
            No trades yet...
          </div>
        ) : (
          recentTrades.map((trade) => (
            <div key={trade.id} className="px-3 py-2 border-b border-[#2d3748]/50 hover:bg-[#1a1f2e]/50">
              <div className="flex justify-between items-center text-xs">
                <span className="text-emerald-400 font-medium">{trade.price}¢</span>
                <span className="text-slate-400">×{trade.quantity}</span>
              </div>
              <div className="flex justify-between items-center text-[10px] text-slate-500 mt-0.5">
                <span className="truncate max-w-[100px]">{trade.buyer_name}</span>
                <span>→</span>
                <span className="truncate max-w-[100px]">{trade.seller_name}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

const SimulationControls = ({
  sessionId,
  isRunning,
  roundNumber,
  onStop,
  questionText,
}: {
  sessionId: string | null
  isRunning: boolean
  roundNumber: number
  onStop: () => void
  questionText: string
}) => {
  return (
    <div className="absolute top-4 left-4 w-80 rounded-lg border-2 border-[#2d3748] bg-[#0f172a]/95 text-[#f7f5f0] shadow-lg z-40">
      <div className="px-3 py-2 border-b border-[#2d3748] bg-[#1a1f2e]">
        <div className="text-sm font-semibold tracking-wider">Simulation</div>
      </div>
      <div className="p-3 space-y-2">
        {questionText && (
          <div className="text-xs text-slate-300 leading-relaxed line-clamp-2">
            {questionText}
          </div>
        )}
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Status:</span>
          <span className={isRunning ? "text-green-400" : "text-slate-500"}>
            {isRunning ? "Running" : "Stopped"}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Round:</span>
          <span className="text-blue-400">{roundNumber}</span>
        </div>
        {sessionId && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Session:</span>
            <span className="text-slate-500 font-mono text-[10px]">{sessionId.slice(0, 8)}...</span>
          </div>
        )}
        {isRunning && (
          <button
            onClick={onStop}
            className="w-full mt-2 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs rounded transition-colors"
          >
            Stop Simulation
          </button>
        )}
      </div>
    </div>
  )
}

const AgentDetailModal = ({
  agent,
  onClose,
}: {
  agent: AgentInfo
  onClose: () => void
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="relative w-full max-w-2xl bg-[#1a1f2e] border-4 border-[#2d3748] rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.75)] p-6 text-white max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white text-2xl font-bold"
        >
          ×
        </button>
        
        <h2 className={`${pressStart.className} text-xl tracking-[0.15em] uppercase mb-4 text-[#f7f5f0]`}>
          {agent.name}
        </h2>
        
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <span className={`px-2 py-1 rounded text-xs ${
              agent.type === "fundamental" ? "bg-blue-900/50 text-blue-300" :
              agent.type === "noise" ? "bg-purple-900/50 text-purple-300" :
              "bg-emerald-900/50 text-emerald-300"
            }`}>
              {agent.type.toUpperCase()}
            </span>
            <span className="text-sm text-slate-400">{agent.role} Agent</span>
          </div>

          <p className="text-gray-300 leading-relaxed">{agent.description}</p>

          {agent.traderState && (
            <div className="p-4 bg-[#0f172a]/50 rounded-lg border border-[#2d3748]">
              <h3 className="text-sm font-semibold mb-3 text-slate-300">Trading State</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-slate-500 text-xs">Position</div>
                  <div className={agent.traderState.position >= 0 ? "text-green-400" : "text-red-400"}>
                    {agent.traderState.position}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500 text-xs">P&L</div>
                  <div className={agent.traderState.pnl >= 0 ? "text-green-400" : "text-red-400"}>
                    ${agent.traderState.pnl.toFixed(2)}
                  </div>
                </div>
              </div>
              
              {agent.traderState.system_prompt && (
                <div className="mt-4 pt-4 border-t border-[#2d3748]">
                  <div className="text-slate-500 text-xs mb-2">Agent Notes</div>
                  <pre className="text-[11px] text-slate-400 whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {agent.traderState.system_prompt}
                  </pre>
                </div>
              )}
            </div>
          )}

          {agent.prediction !== undefined && (
            <div className="text-center py-4">
              <div className="text-slate-500 text-sm mb-1">Last Prediction</div>
              <div className={`${pressStart.className} text-4xl text-emerald-400`}>
                {agent.prediction}¢
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const PriceGraphModal = ({
  open,
  onClose,
  sessionId,
}: {
  open: boolean
  onClose: () => void
  sessionId: string | null
}) => {
  const [orderBook, setOrderBook] = useState<{ bids: any[], asks: any[] }>({ bids: [], asks: [] })
  
  useEffect(() => {
    if (!open || !sessionId) return
    
    // Fetch orderbook from API
    const fetchOrderBook = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sessions/${sessionId}/orderbook`)
        if (response.ok) {
          const data = await response.json()
          setOrderBook(data)
        }
      } catch (error) {
        console.error("Error fetching orderbook:", error)
      }
    }
    
    fetchOrderBook()
    const interval = setInterval(fetchOrderBook, 2000)
    return () => clearInterval(interval)
  }, [open, sessionId])
  
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="relative w-full max-w-6xl h-[58vh] rounded-xl border-4 border-[#2d3748] bg-[#0f172a]/95 text-[#f7f5f0] shadow-[0_20px_40px_rgba(0,0,0,0.55)] px-8 py-6">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 px-3 py-1 bg-red-500 text-white text-xs rounded-md shadow hover:bg-red-600 transition-colors z-10"
        >
          Close
        </button>

        <div className="text-center text-2xl mb-4 mt-2 tracking-[0.15em]">Market Price</div>

        <PriceGraph sessionId={sessionId} />
      </div>
    </div>
  )
}

function OfficePageContent() {
  const { initializeDemoAgents } = useTradingStore()
  const [orderBookOpen, setOrderBookOpen] = useState(false)
  const searchParams = useSearchParams()
  
  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [questionText, setQuestionText] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [forecasterResponses, setForecasterResponses] = useState<ForecasterResponse[]>([])
  const [selectedForecaster, setSelectedForecaster] = useState<ForecasterResponse | null>(null)
  const [traderFlashStates, setTraderFlashStates] = useState<Record<string, "buy" | "sell" | null>>({})
  const processingRef = useRef<string | null>(null) // Track which query is currently being processed
  const lastProcessedQueryRef = useRef<string | null>(null) // Track last successfully processed query

  useEffect(() => {
    initializeDemoAgents(18)
  }, [initializeDemoAgents])

  // Poll simulation status
  useEffect(() => {
    if (!sessionId) return
    
    const pollStatus = async () => {
      try {
        const status = await api.sessions.getStatus(sessionId)
        setIsRunning(status.running)
        setRoundNumber(status.round_number || 0)
        // Update phase from backend (initializing, running, stopped)
        if (status.phase) {
          setSimulationPhase(status.phase as "initializing" | "running" | "stopped")
        }
      } catch (error) {
        console.error("Error polling status:", error)
      }
    }
    
    pollStatus()
    // Poll more frequently during initialization to catch phase changes
    const interval = setInterval(pollStatus, 3000)
    return () => clearInterval(interval)
  }, [sessionId])

  // Build agents with real-time state
  // Agent status is tied to the simulation phase and trader state
  const agents: AgentInfo[] = ALL_AGENTS.map((agentConfig) => {
    const traderState = realtimeData.traderStates.find(
      (t) => t.name === agentConfig.key || t.name === agentConfig.key.toLowerCase()
    )
    
    // Status logic:
    // - offline: simulation stopped
    // - analyzing: initializing phase (superforecasters running)
    // - idle: simulation running and trader is active
    let status: "idle" | "analyzing" | "offline"
    if (simulationPhase === "stopped") {
      status = "offline"
    } else if (simulationPhase === "initializing") {
      status = "analyzing"  // Yellow - processing
    } else {
      setForecasterResponses([])
    }
  }, [forecast?.id, forecast?.forecaster_responses])

  // Subscribe to real-time forecaster_responses updates to show progress
  useEffect(() => {
    if (!forecast?.id) return

    const channel = supabase
      .channel(`forecaster_responses:${forecast.id}`)
      .on(
        "postgres_changes",
        {
          event: "*", // Listen to INSERT, UPDATE, DELETE
          schema: "public",
          table: "forecaster_responses",
          filter: `session_id=eq.${forecast.id}`,
        },
        async (payload) => {
          // Fetch updated forecast data when forecaster responses change
          try {
            const forecastData = await api.forecasts.get(forecast.id) as Forecast
            if (forecastData.forecaster_responses) {
              setForecasterResponses(forecastData.forecaster_responses)
              setForecast(forecastData)
            }
          } catch (error) {
            console.error("Error fetching updated forecaster responses:", error)
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [forecast?.id])

  // Subscribe to real-time orderbook changes to flash trader status dots
  useEffect(() => {
    if (!forecast?.id) return

    const channel = supabase
      .channel(`trader_flash:${forecast.id}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "orderbook_live",
          filter: `session_id=eq.${forecast.id}`,
        },
        (payload) => {
          const newOrder = payload.new as { trader_name: string; side: "buy" | "sell" }
          const traderName = newOrder.trader_name
          const side = newOrder.side

          // Flash the trader's status dot
          setTraderFlashStates((prev) => ({
            ...prev,
            [traderName]: side,
          }))

          // Clear the flash after 2 seconds
          setTimeout(() => {
            setTraderFlashStates((prev) => {
              const updated = { ...prev }
              if (updated[traderName] === side) {
                updated[traderName] = null
              }
              return updated
            })
          }, 2000)
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [forecast?.id])

  // Cleanup: Mark session as completed when component unmounts or page closes
  useEffect(() => {
    if (!forecast?.id) return

    const markSessionCompleted = async () => {
      try {
        await api.sessions.complete(forecast.id)
      } catch (error) {
        console.error("Error marking session as completed:", error)
      }
    }

    // Mark as completed when component unmounts (user navigates away)
    const handleBeforeUnload = () => {
      // Use sendBeacon with GET request for reliable delivery even if page is closing
      const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sessions/${forecast.id}/complete`
      navigator.sendBeacon(url)
    }

    // Handle page visibility change (tab switch, minimize, etc.)
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        // Page is being hidden, mark session as completed
        markSessionCompleted()
      }
    }

    // Add event listeners
    window.addEventListener("beforeunload", handleBeforeUnload)
    document.addEventListener("visibilitychange", handleVisibilityChange)

    // Return cleanup function for component unmount
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload)
      document.removeEventListener("visibilitychange", handleVisibilityChange)
      // Mark as completed on unmount
      markSessionCompleted()
    }
  }, [forecast?.id])

  const processForecast = async (queryText: string) => {
    // Normalize query text for comparison
    const normalizedQuery = queryText.trim().toLowerCase()
    
    // Prevent duplicate processing of the same query
    if (processingRef.current === normalizedQuery) {
      console.log("Already processing this query, skipping duplicate call")
      return
    }
    
    // If we already processed this exact query, don't process again
    if (lastProcessedQueryRef.current === normalizedQuery && forecast?.id) {
      console.log("Query already processed, using existing forecast")
      return
    }
    
    // Mark as processing
    processingRef.current = normalizedQuery
    
    setIsLoading(true)
    setForecast(null)
    setForecasterResponses([])

    try {
      // Check if forecast exists in database (any status, not just completed)
      const existingForecasts = await api.forecasts.list(10, 0, queryText.trim()) as { forecasts: Forecast[], total: number }
      let forecastId: string | null = null
      let existingForecast: Forecast | null = null

      if (existingForecasts.forecasts && existingForecasts.forecasts.length > 0) {
        // Find any forecast with matching question (prefer most recent)
        const matching = existingForecasts.forecasts
          .filter((f) => f.question_text.trim().toLowerCase() === queryText.trim().toLowerCase())
          .sort((a, b) => {
            // Sort by created_at descending (most recent first)
            const aDate = new Date(a.created_at).getTime()
            const bDate = new Date(b.created_at).getTime()
            return bDate - aDate
          })
        
        if (matching.length > 0) {
          existingForecast = matching[0]
          forecastId = existingForecast.id
        }
      }

      // If no existing forecast found, create a new one
      if (!forecastId) {
        const newForecast = await api.forecasts.create({
          question_text: queryText.trim(),
          question_type: "binary",
          run_all_forecasters: true, // Run all 5 forecaster personalities for Cassandra
          agent_counts: {
            phase_1_discovery: 2,
            phase_2_validation: 2,
            phase_3_research: 2, // Backward compatible - will split 50/50 into historical/current
            phase_4_synthesis: 1,
          },
        }) as Forecast
        forecastId = newForecast.id

        // Poll for updates - update UI continuously to show progress
        const pollInterval = setInterval(async () => {
          try {
            const forecastData = await api.forecasts.get(forecastId!) as Forecast
            const responses = forecastData.forecaster_responses || []
            
            // Always update the UI with latest data (not just when completed)
            setForecast(forecastData)
            setForecasterResponses(responses)
            setIsLoading(false)
            
            // Check if all forecasters are completed (or at least one failed)
            const allCompleted = responses.length >= 5 && responses.every(r => 
              r.status === "completed" || r.status === "failed"
            )
            
            if (allCompleted || forecastData.status === "failed") {
              clearInterval(pollInterval)
              // Don't show result overlay - show office with forecasters instead
            }
          } catch (error) {
            console.error("Error polling forecast:", error)
            clearInterval(pollInterval)
            setIsLoading(false)
          }
        }, 2000) // Poll every 2 seconds

        // Timeout after 5 minutes
        setTimeout(() => {
          clearInterval(pollInterval)
          if (isLoading) {
            setIsLoading(false)
            alert("Forecast is taking longer than expected. Please check back later.")
          }
        }, 300000)
        
        // Mark as processed
        lastProcessedQueryRef.current = normalizedQuery
        processingRef.current = null
      } else {
        // Use existing forecast - resume session
        const forecastData = await api.forecasts.get(forecastId) as Forecast
        setForecast(forecastData)
        if (forecastData.forecaster_responses) {
          setForecasterResponses(forecastData.forecaster_responses)
          
          // Check if all forecasters are completed
          const allCompleted = forecastData.forecaster_responses.length >= 5 && 
            forecastData.forecaster_responses.every(r => 
              r.status === "completed" || r.status === "failed"
            )
          
          // If forecasters are completed, automatically start/resume trading
          if (allCompleted && forecastId) {
            try {
              await api.sessions.startTrading(forecastId, 30, false)
              console.log("Trading resumed for existing session")
            } catch (error) {
              console.error("Error resuming trading:", error)
            }
          } else if (forecastId) {
            // Forecasters still running, wait for them to complete
            // Poll for completion and then start trading - update UI continuously
            const pollInterval = setInterval(async () => {
              try {
                const updatedForecast = await api.forecasts.get(forecastId!) as Forecast
                const responses = updatedForecast.forecaster_responses || []
                
                // Always update the UI with latest data (not just when completed)
                setForecast(updatedForecast)
                setForecasterResponses(responses)
                
                const allCompleted = responses.length >= 5 && responses.every(r => 
                  r.status === "completed" || r.status === "failed"
                )
                
                if (allCompleted) {
                  clearInterval(pollInterval)
                  
                  // Start trading now that forecasters are done
                  if (forecastId) {
                    try {
                      await api.sessions.startTrading(forecastId, 30, false)
                      console.log("Trading started after forecasters completed")
                    } catch (error) {
                      console.error("Error starting trading:", error)
                    }
                  }
                }
              } catch (error) {
                console.error("Error polling forecast:", error)
                clearInterval(pollInterval)
              }
            }, 2000)
            
            // Timeout after 5 minutes
            setTimeout(() => {
              clearInterval(pollInterval)
            }, 300000)
          }
        }
        
        // Mark as processed
        lastProcessedQueryRef.current = normalizedQuery
        processingRef.current = null
        setIsLoading(false)
      }
    } catch (error) {
      console.error("Error processing forecast:", error)
      processingRef.current = null // Clear processing flag on error
      setIsLoading(false)
      alert("Failed to start simulation. Please try again.")
    }
  }, [])

  // Stop simulation
  const stopSimulation = useCallback(async () => {
    if (!sessionId) return
    
    try {
      await api.sessions.stop(sessionId)
      setIsRunning(false)
    } catch (error) {
      console.error("Error stopping simulation:", error)
    }
  }, [sessionId])

  // Track if we've already started a simulation (prevents React Strict Mode double-call)
  const hasStartedRef = useRef(false)

  // Handle query param
  useEffect(() => {
    const query = searchParams.get("q")
    if (query) {
      const normalizedQuery = query.trim().toLowerCase()
      // Only process if this is a different query than what we last processed
      if (lastProcessedQueryRef.current !== normalizedQuery) {
        processForecast(query)
      }
    }
  }, [searchParams, sessionId, startSimulation])

  return (
    <div className="h-screen w-full flex flex-col items-center justify-center relative overflow-hidden font-pixel">
      <style jsx global>{`
        .pixelated {
          image-rendering: pixelated;
        }
      `}</style>

      {/* Background image */}
      <div className="absolute inset-0 z-0">
        <Image
          src="/officebackground3.png"
          alt="Office floor background"
          fill
          priority
          sizes="100vw"
          className="object-fill"
          style={{ imageRendering: "pixelated" }}
        />
        <div className="absolute inset-0 bg-black/10" />
      </div>

      {/* Simulation Controls */}
      <SimulationControls
        sessionId={sessionId}
        isRunning={isRunning}
        roundNumber={roundNumber}
        onStop={stopSimulation}
        questionText={questionText}
      />

      {/* Trade Feed */}
      <TradeFeed trades={realtimeData.trades} />

      {/* Main Scene */}
      <div className="relative z-10 w-full h-full">
        <OfficeScene 
          forecasterResponses={forecasterResponses}
          onForecasterClick={(response) => setSelectedForecaster(response)}
          traderFlashStates={traderFlashStates}
        />

        {/* Central desk / terminal in the aisle */}
        <div className="absolute inset-0 flex items-center justify-center z-30 pointer-events-none">
          <button
            onClick={() => setOrderBookOpen(true)}
            className="relative group p-4 rounded-lg bg-transparent pointer-events-auto"
            aria-label="Open market price graph"
          >
            <img
              src="/sprites/desk-with-pc.png"
              alt="Desk terminal"
              className="w-24 h-24 object-contain pixelated drop-shadow-[0_10px_15px_rgba(0,0,0,0.45)] transition-transform duration-150 group-hover:-translate-y-1"
            />
            <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 -top-10 px-3 py-1 rounded-md bg-slate-900/90 text-[11px] text-slate-100 border border-white/10 shadow opacity-0 group-hover:opacity-100 transition-opacity duration-150 whitespace-nowrap">
              View Market Price
            </div>
          </button>
        </div>
      </div>

      <PriceGraphModal 
        open={orderBookOpen} 
        onClose={() => setOrderBookOpen(false)} 
        sessionId={forecast?.id || null}
      />

      {/* Loading overlay */}
      {isLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3 text-[#f7f5f0] drop-shadow-[0_4px_12px_rgba(0,0,0,0.55)]">
            <div className="text-xl tracking-[0.18em] uppercase flex items-center gap-1">
              <span>Starting Simulation</span>
              <span className="inline-flex w-10 justify-between text-lg">
                <span className="animate-[blink_1s_infinite]">.</span>
                <span className="animate-[blink_1.1s_infinite]">.</span>
                <span className="animate-[blink_1.2s_infinite]">.</span>
              </span>
            </div>
            <div className="text-sm text-slate-400">Running superforecasters...</div>
            <div className="h-1.5 w-28 overflow-hidden rounded-full bg-white/20 relative">
              <div className="absolute inset-y-0 left-0 w-1/3 animate-[slide_1.8s_ease-in-out_infinite] bg-white/60 rounded-full" />
            </div>
          </div>
        </div>
      )}

      {/* Agent Detail Modal */}
      {selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          onClose={() => setSelectedAgent(null)}
        />
      )}

      {/* CRT/Scanline Effects */}
      <div className="fixed inset-0 pointer-events-none z-50 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.12)_50%),linear-gradient(90deg,rgba(255,0,0,0.05),rgba(0,255,0,0.02),rgba(0,0,255,0.05))] bg-[length:100%_2px,3px_100%] opacity-25 mix-blend-overlay" />
      <div className="fixed inset-0 pointer-events-none z-50 shadow-[inset_0_0_120px_rgba(0,0,0,0.82)]" />
    </div>
  )
}

export default function Page() {
  return (
    <Suspense fallback={
      <div className="h-screen w-full flex items-center justify-center bg-[#0f172a]">
        <div className="text-white">Loading...</div>
      </div>
    }>
      <OfficePageContent />
    </Suspense>
  )
}
