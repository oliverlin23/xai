"use client"

import { useEffect, useState, Suspense, useCallback } from "react"
import { useTradingStore } from "@/lib/store"
import { useSearchParams } from "next/navigation"
import Image from "next/image"
import { api } from "@/lib/api"
import { useRealtimeTrades, Trade, TraderState, FlashingTrader } from "@/hooks/useRealtimeTrades"
import { Press_Start_2P } from "next/font/google"
import { PriceGraph } from "@/components/trading/PriceGraph"

const pressStart = Press_Start_2P({ weight: "400", subsets: ["latin"] })

// Module-level tracking to prevent React Strict Mode double-init
// This persists across component remounts but not page refreshes
let startedSimulationQuery: string | null = null

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

// Choose sprite for a given agent
const getAgentSprite = (agent: { key: string; type: string }, index: number) => {
  if (agent.type === "user" && agent.key === "owen") {
    return "/sprites/owenzhanggood.png"
  }
  else if (agent.type == "user" && agent.key == "skylar"){
    return "/sprites/skylargood.png"
  }
  else if (agent.type == "user" && agent.key == "oliver"){
    return "/sprites/olivergood.png"
  }
  else if (agent.type == "user" && agent.key == "tyler"){
    return "/sprites/tylergood.png"
  }
  return workerSprites[index % workerSprites.length]
}

const statusStyles = {
  idle: { label: "Active", className: "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.45)]" },
  analyzing: { label: "Processing", className: "bg-yellow-400 shadow-[0_0_10px_rgba(234,179,8,0.45)]" },
  "submitting-order": { label: "Submitting", className: "bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.45)]" },
  offline: { label: "Offline", className: "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.45)]" },
  buying: { label: "Buying", className: "bg-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.7)] animate-pulse" },
  selling: { label: "Selling", className: "bg-red-400 shadow-[0_0_15px_rgba(248,113,113,0.7)] animate-pulse" },
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
  description?: string
  prediction?: number
  onClick?: () => void
  hasPlant?: boolean
  hasTrash?: boolean
}) => {
  const statusMeta = statusStyles[status]

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
  status: "idle" | "analyzing" | "offline" | "buying" | "selling"
  prediction?: number
  traderState?: TraderState
}

const OfficeScene = ({ 
  agents,
  onAgentClick,
}: { 
  agents: AgentInfo[]
  onAgentClick: (agent: AgentInfo) => void
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
                  sprite={getAgentSprite(agent, i)}
                  name={agent.name}
                  role={agent.role}
                  status={agent.status}
                  description={agent.description}
                  prediction={agent.prediction}
                  onClick={() => onAgentClick(agent)}
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
                    sprite={getAgentSprite(agent, idx)}
                    name={agent.name}
                    role={agent.role}
                    status={agent.status}
                    description={agent.description}
                    prediction={agent.prediction}
                    onClick={() => onAgentClick(agent)}
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
            <div 
              key={trade.id} 
              className="px-3 py-2 border-b border-[#2d3748]/50 hover:bg-[#1a1f2e]/50"
            >
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
  simulationPhase,
  roundNumber,
  onStop,
  questionText,
}: {
  sessionId: string | null
  isRunning: boolean
  simulationPhase: "initializing" | "running" | "stopped"
  roundNumber: number
  onStop: () => void
  questionText: string
}) => {
  // Determine status text and color based on phase
  const getStatusDisplay = () => {
    switch (simulationPhase) {
      case "initializing":
        return { text: "Initializing...", color: "text-yellow-400" }
      case "running":
        return { text: "Running", color: "text-green-400" }
      case "stopped":
      default:
        return { text: "Stopped", color: "text-slate-500" }
    }
  }
  
  const statusDisplay = getStatusDisplay()
  
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
          <span className={statusDisplay.color}>
            {statusDisplay.text}
          </span>
        </div>
        {simulationPhase === "initializing" && (
          <div className="text-[10px] text-slate-500 italic">
            Superforecasters analyzing market...
          </div>
        )}
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
              <div className="text-sm">
                <div>
                  <div className="text-slate-500 text-xs">Position</div>
                  <div className={agent.traderState.position >= 0 ? "text-green-400" : "text-red-400"}>
                    {agent.traderState.position}
                  </div>
                </div>
              </div>
              
              {agent.traderState.system_prompt && (
                <div className="mt-4 pt-4 border-t border-[#2d3748]">
                  <div className="text-slate-500 text-xs mb-2">Notes:</div>
                  <pre className="text-[11px] text-slate-400 whitespace-pre-wrap max-h-48 overflow-y-auto bg-[#0a0f1a] p-3 rounded border border-[#2d3748]/50">
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
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="relative w-full max-w-6xl h-[70vh] rounded-xl border-4 border-[#2d3748] bg-[#0f172a]/95 text-[#f7f5f0] shadow-[0_20px_40px_rgba(0,0,0,0.55)] px-6 py-6 overflow-hidden">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 px-3 py-1 bg-red-500 text-white text-xs rounded-md shadow"
        >
          Close
        </button>

        <div className="text-center text-2xl mb-4 tracking-[0.15em]">Market Price</div>

        <div className="h-full">
          <PriceGraph sessionId={sessionId} />
        </div>
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
  const [isRunning, setIsRunning] = useState(false)
  const [simulationPhase, setSimulationPhase] = useState<"initializing" | "running" | "stopped">("stopped")
  const [roundNumber, setRoundNumber] = useState(0)
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null)
  
  // Real-time data
  const realtimeData = useRealtimeTrades(sessionId || "")

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
  // Agent status is ONLY tied to recent trades - yellow by default, flash on trade
  const agents: AgentInfo[] = ALL_AGENTS.map((agentConfig) => {
    const traderState = realtimeData.traderStates.find(
      (t) => t.name === agentConfig.key || t.name === agentConfig.key.toLowerCase()
    )
    
    // Check if this agent is flashing from a recent trade
    const flashingInfo = realtimeData.flashingTraders.find(
      (f) => f.name === agentConfig.key || f.name === agentConfig.key.toLowerCase()
    )

    // Status logic:
    // - buying: agent just bought (flash green)
    // - selling: agent just sold (flash red)
    // - analyzing: default state (yellow)
    let status: "idle" | "analyzing" | "offline" | "buying" | "selling"
    
    if (flashingInfo) {
      status = flashingInfo.type === "buyer" ? "buying" : "selling"
    } else {
      status = "analyzing"  // Default: yellow
    }

    return {
      ...agentConfig,
      status,
      prediction: undefined, // Could extract from system_prompt if stored
      traderState,
    }
  })

  // Start simulation
  const startSimulation = useCallback(async (queryText: string) => {
    setIsLoading(true)
    setQuestionText(queryText)

    try {
      const result = await api.sessions.run({
        question_text: queryText.trim(),
        question_type: "binary",
        resolution_criteria: "Standard YES/NO resolution based on outcome occurrence.",
        resolution_date: "2025-12-31",
        trading_interval_seconds: 10,
      })

      setSessionId(result.session_id)
      // Set to initializing immediately - polling will update to "running" once simulation starts
      setSimulationPhase("initializing")
      setIsLoading(false)
    } catch (error) {
      console.error("Error starting simulation:", error)
      setIsLoading(false)
      setSimulationPhase("stopped")
      alert("Failed to start simulation. Please try again.")
    }
  }, [])

  // Stop simulation
  const stopSimulation = useCallback(async () => {
    if (!sessionId) return
    
    try {
      await api.sessions.stop(sessionId)
      setIsRunning(false)
      setSimulationPhase("stopped")
    } catch (error) {
      console.error("Error stopping simulation:", error)
    }
  }, [sessionId])

  // Handle query param - use module-level tracking to survive Strict Mode remounts
  // DO NOT reset startedSimulationQuery on unmount - Strict Mode unmounts/remounts
  // and we need to prevent the second mount from starting another simulation
  useEffect(() => {
    const query = searchParams.get("q")
    // Only start if: query exists, no session yet, and this query hasn't already started
    if (query && !sessionId && startedSimulationQuery !== query) {
      startedSimulationQuery = query
      startSimulation(query)
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
        simulationPhase={simulationPhase}
        roundNumber={roundNumber}
        onStop={stopSimulation}
        questionText={questionText}
      />

      {/* Trade Feed */}
      <TradeFeed trades={realtimeData.trades} />

      {/* Main Scene */}
      <div className="relative z-10 w-full h-full">
        <OfficeScene
          agents={agents}
          onAgentClick={(agent) => setSelectedAgent(agent)}
        />

        {/* Central desk / terminal in the aisle */}
        <div className="absolute inset-0 flex items-center justify-center z-30 pointer-events-none">
          <button
            onClick={() => setOrderBookOpen(true)}
            className="relative group p-4 rounded-lg bg-transparent pointer-events-auto"
            aria-label="Open market price"
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
        sessionId={sessionId}
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