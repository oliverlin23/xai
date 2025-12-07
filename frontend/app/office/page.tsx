"use client"

import { useEffect, useState, Suspense } from "react"
import { useTradingStore } from "@/lib/store"
import { useDemoMode } from "@/hooks/useDemoMode"
import { useSearchParams } from "next/navigation"
import Image from "next/image"
import { api } from "@/lib/api"
import { Forecast, ForecasterResponse } from "@/types/forecast"
import { FORECASTER_CLASSES } from "@/lib/forecasterClasses"
import { Press_Start_2P } from "next/font/google"

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

const roles = ["Trader", "Quant", "Analyst", "Execution"]

const statusStyles = {
  idle: { label: "Active", className: "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.45)]" },
  analyzing: { label: "Processing", className: "bg-yellow-400 shadow-[0_0_10px_rgba(234,179,8,0.45)]" },
  "submitting-order": { label: "Submitting", className: "bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.45)]" },
  offline: { label: "Offline", className: "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.45)]" },
}

const demoOrderBook = {
  asks: [
    { price: 0.44, size: 1200 },
    { price: 0.36, size: 950 },
    { price: 0.35, size: 820 },
    { price: 0.33, size: 640 },
  ],
  bids: [
    { price: 0.30, size: 1180 },
    { price: 0.29, size: 980 },
    { price: 0.28, size: 840 },
    { price: 0.27, size: 710 },
  ],
}

const PartitionFrame = () => (
  <>
    <img
      src="/sprites/office-partitions-1.png"
      className="absolute -top-6 left-0 w-full h-full object-contain pixelated opacity-80pointer-events-none z-10"
      alt="partition top"
    />
    <img
      src="/sprites/office-partitions-2.png"
      className="absolute -top-6 right-1/2 w-full h-full object-contain pixelated opacity-80pointer-events-none z-10"
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
  probability,
  confidence,
  onClick,
  hasPlant = false,
  hasTrash = false,
}: {
  sprite: string
  name: string
  role: string
  status: keyof typeof statusStyles
  description?: string
  probability?: number
  confidence?: number
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
        {/* Hover card - expanded to show description */}
        <div className="pointer-events-none absolute -top-2 left-1/2 -translate-x-1/2 -translate-y-full z-40 px-3 py-2 rounded-md bg-slate-900/90 border border-white/10 shadow-lg text-xs text-slate-100 opacity-0 transition-opacity duration-150 group-hover:opacity-100 max-w-xs">
          <div className="font-semibold mb-1">{name}</div>
          <div className="text-[11px] text-slate-300 mb-1">Role: {role}</div>
          {description && (
            <div className="text-[10px] text-slate-400 mt-2 mb-2 leading-relaxed whitespace-normal max-w-[200px]">
              {description}
            </div>
          )}
          {(probability !== undefined || confidence !== undefined) && (
            <div className="mt-2 pt-2 border-t border-white/10">
              {probability !== undefined && (
                <div className="text-[10px] text-slate-300">
                  Probability: {Math.round(probability * 100)}%
                </div>
              )}
              {confidence !== undefined && (
                <div className="text-[10px] text-blue-300">
                  Confidence: {Math.round(confidence * 100)}%
                </div>
              )}
            </div>
          )}
          <div className="text-[9px] text-slate-500 mt-2 italic">Click for details</div>
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

const OfficeScene = ({ 
  forecasterResponses, 
  onForecasterClick 
}: { 
  forecasterResponses: ForecasterResponse[]
  onForecasterClick: (response: ForecasterResponse) => void
}) => {
  // Map the 5 forecaster responses to cubicles (first 5 positions)
  // Fill remaining with placeholders
  type AgentInfo = {
    id: string
    name: string
    role: string
    status: "idle" | "analyzing" | "offline"
    description?: string
    probability?: number
    confidence?: number
    response?: ForecasterResponse
  }
  
  const activeAgents: AgentInfo[] = Array.from({ length: 18 }, (_, i) => {
    if (forecasterResponses[i]) {
      const response = forecasterResponses[i]
      const classInfo = FORECASTER_CLASSES[response.forecaster_class as keyof typeof FORECASTER_CLASSES]
      return {
        id: response.id,
        name: classInfo?.name || response.forecaster_class,
        role: "Forecaster",
        status: response.status === "completed" ? "idle" as const : 
                response.status === "running" ? "analyzing" as const : 
                "offline" as const,
        description: classInfo?.description || "",
        probability: response.prediction_probability,
        confidence: response.confidence,
        response: response,
      }
    }
    return {
      id: `placeholder-${i}`,
      name: `Agent ${i + 1}`,
      role: roles[i % roles.length],
      status: "idle" as const,
    }
  })

  return (
    <div className="relative w-full h-full flex items-center justify-center p-0">
      <div className="relative z-10 w-full h-full flex flex-col justify-between">
        {/* Main Office Floor */}
        <div className="flex-1 flex items-center justify-center gap-52 px-6 pt-48">
          {/* Left Bank */}
          <div className="grid grid-cols-3 gap-x-0 gap-y-0">
            {activeAgents.slice(0, 9).map((agent, i) => (
              <div key={agent.id} className="flex justify-center">
                <Cubicle
                  sprite={workerSprites[i % workerSprites.length]}
                  name={agent.name}
                  role={agent.role}
                  status={agent.status}
                  description={agent.description}
                  probability={agent.probability}
                  confidence={agent.confidence}
                  onClick={agent.response ? () => onForecasterClick(agent.response) : undefined}
                  hasPlant={false}
                  hasTrash={i % 4 === 1}
                />
              </div>
            ))}
          </div>

          {/* Right Bank */}
          <div className="grid grid-cols-3 gap-x-0 gap-y-0">
            {activeAgents.slice(9, 18).map((agent, i) => {
              const idx = i + 9
              return (
                <div key={agent.id} className="flex justify-center">
                  <Cubicle
                    sprite={workerSprites[idx % workerSprites.length]}
                    name={agent.name}
                    role={agent.role}
                    status={agent.status}
                    description={agent.description}
                    probability={agent.probability}
                    confidence={agent.confidence}
                    onClick={agent.response ? () => onForecasterClick(agent.response) : undefined}
                    hasPlant={false}
                    hasTrash={idx % 4 === 1}
                  />
                </div>
              )
            })}
          </div>
        </div>

        {/*
        <div className="relative pt-6 mt-6 flex justify-center pb-6">

          <div className="relative">
            <Cubicle
              sprite="/sprites/boss.png"
              name="Director Joja"
              role="Overseer"
              status="analyzing"
              hasPlant
            />
          </div>
        </div>
        */}
      </div>
    </div>
  )
}

const OrderBookModal = ({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) => {
  if (!open) return null

  const maxAskSize = Math.max(...demoOrderBook.asks.map((a) => a.size), 1)
  const maxBidSize = Math.max(...demoOrderBook.bids.map((b) => b.size), 1)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="relative w-full max-w-3xl rounded-xl border-4 border-[#2d3748] bg-[#0f172a]/95 text-[#f7f5f0] shadow-[0_20px_40px_rgba(0,0,0,0.55)] p-6">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 px-3 py-1 bg-red-500 text-white text-xs rounded-md shadow"
        >
          Close
        </button>

        <div className="text-center text-2xl mb-4 tracking-[0.15em]">Order Book</div>

        <div className="space-y-4">
          <div className="border border-red-400/40 rounded-lg p-4 bg-red-900/25 shadow-inner">
            <div className="text-red-300 text-lg mb-2 tracking-[0.1em]">Asks</div>
            <div className="space-y-2">
              {demoOrderBook.asks.map((ask, idx) => {
                const widthPct = Math.max((ask.size / maxAskSize) * 100, 6)
                return (
                  <div
                    key={idx}
                    className="relative flex items-center text-sm bg-red-900/35 border border-red-500/30 rounded px-3 py-2 overflow-hidden"
                  >
                    <div
                      className="absolute left-0 top-0 h-full bg-red-600/30"
                      style={{ width: `${widthPct}%` }}
                    />
                    <div className="relative flex-1 flex justify-between items-center">
                      <span className="text-red-200 font-semibold">{Math.round(ask.price * 100)}¢</span>
                      <span className="text-red-100">{ask.size.toLocaleString()}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="border border-emerald-400/40 rounded-lg p-4 bg-emerald-900/25 shadow-inner">
            <div className="text-emerald-300 text-lg mb-2 tracking-[0.1em]">Bids</div>
            <div className="space-y-2">
              {demoOrderBook.bids.map((bid, idx) => {
                const widthPct = Math.max((bid.size / maxBidSize) * 100, 6)
                return (
                  <div
                    key={idx}
                    className="relative flex items-center text-sm bg-emerald-900/35 border border-emerald-500/30 rounded px-3 py-2 overflow-hidden"
                  >
                    <div
                      className="absolute left-0 top-0 h-full bg-emerald-600/30"
                      style={{ width: `${widthPct}%` }}
                    />
                    <div className="relative flex-1 flex justify-between items-center">
                      <span className="text-emerald-200 font-semibold">{Math.round(bid.price * 100)}¢</span>
                      <span className="text-emerald-100">{bid.size.toLocaleString()}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function OfficePageContent() {
  const { initializeDemoAgents } = useTradingStore()
  const [orderBookOpen, setOrderBookOpen] = useState(false)
  const searchParams = useSearchParams()
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [forecasterResponses, setForecasterResponses] = useState<ForecasterResponse[]>([])
  const [selectedForecaster, setSelectedForecaster] = useState<ForecasterResponse | null>(null)

  useEffect(() => {
    initializeDemoAgents(18)
  }, [initializeDemoAgents])

  // Fetch forecaster responses when forecast is available
  useEffect(() => {
    if (forecast?.forecaster_responses) {
      setForecasterResponses(forecast.forecaster_responses)
    } else if (forecast?.id) {
      // If responses not in forecast object, fetch them
      const fetchResponses = async () => {
        try {
          const forecastData = await api.forecasts.get(forecast.id) as Forecast
          if (forecastData.forecaster_responses) {
            setForecasterResponses(forecastData.forecaster_responses)
          }
        } catch (error) {
          console.error("Error fetching forecaster responses:", error)
        }
      }
      fetchResponses()
    } else {
      setForecasterResponses([])
    }
  }, [forecast?.id, forecast?.forecaster_responses])

  const processForecast = async (queryText: string) => {
    setIsLoading(true)
    setForecast(null)
    setForecasterResponses([])

    try {
      // Check if forecast exists in database
      const existingForecasts = await api.forecasts.list(1, 0, queryText.trim()) as { forecasts: Forecast[], total: number }
      let forecastId: string | null = null

      if (existingForecasts.forecasts && existingForecasts.forecasts.length > 0) {
        // Find a completed forecast with matching question
        const completed = existingForecasts.forecasts.find(
          (f) => f.status === "completed" && f.question_text.trim().toLowerCase() === queryText.trim().toLowerCase()
        )
        if (completed) {
          forecastId = completed.id
        }
      }

      // If no completed forecast found, create a new one
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

        // Poll for completion - check if all 5 forecasters are completed
        const pollInterval = setInterval(async () => {
          try {
            const forecastData = await api.forecasts.get(forecastId!) as Forecast
            const responses = forecastData.forecaster_responses || []
            
            // Check if all forecasters are completed (or at least one failed)
            const allCompleted = responses.length >= 5 && responses.every(r => 
              r.status === "completed" || r.status === "failed"
            )
            
            if (allCompleted || forecastData.status === "failed") {
              clearInterval(pollInterval)
              setForecast(forecastData)
              setForecasterResponses(responses)
              setIsLoading(false)
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
      } else {
        // Use existing forecast
        const forecastData = await api.forecasts.get(forecastId) as Forecast
        setForecast(forecastData)
        if (forecastData.forecaster_responses) {
          setForecasterResponses(forecastData.forecaster_responses)
        }
        setIsLoading(false)
      }
    } catch (error) {
      console.error("Error processing forecast:", error)
      setIsLoading(false)
      alert("Failed to process your query. Please try again.")
    }
  }

  useEffect(() => {
    const query = searchParams.get("q")
    if (query) {
      processForecast(query)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])


  useDemoMode(true)

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

      {/* Main Scene */}
      <div className="relative z-10 w-full h-full">
        <OfficeScene 
          forecasterResponses={forecasterResponses}
          onForecasterClick={(response) => setSelectedForecaster(response)}
        />

        {/* Central desk / terminal in the aisle */}
        <div className="absolute inset-0 flex items-center justify-center z-30 pointer-events-none">
          <button
            onClick={() => setOrderBookOpen(true)}
            className="relative group p-4 rounded-lg bg-transparent pointer-events-auto"
            aria-label="Open order book terminal"
          >
            <img
              src="/sprites/desk-with-pc.png"
              alt="Desk terminal"
              className="w-24 h-24 object-contain pixelated drop-shadow-[0_10px_15px_rgba(0,0,0,0.45)] transition-transform duration-150 group-hover:-translate-y-1"
            />
            <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 -top-10 px-3 py-1 rounded-md bg-slate-900/90 text-[11px] text-slate-100 border border-white/10 shadow opacity-0 group-hover:opacity-100 transition-opacity duration-150 whitespace-nowrap">
              View Order Book
            </div>
          </button>
        </div>
      </div>

      <OrderBookModal open={orderBookOpen} onClose={() => setOrderBookOpen(false)} />

      {/* Loading overlay */}
      {isLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3 text-[#f7f5f0] drop-shadow-[0_4px_12px_rgba(0,0,0,0.55)]">
            <div className="text-xl tracking-[0.18em] uppercase flex items-center gap-1">
              <span>Analyzing</span>
              <span className="inline-flex w-10 justify-between text-lg">
                <span className="animate-[blink_1s_infinite]">.</span>
                <span className="animate-[blink_1.1s_infinite]">.</span>
                <span className="animate-[blink_1.2s_infinite]">.</span>
              </span>
            </div>
            <div className="h-1.5 w-28 overflow-hidden rounded-full bg-white/20 relative">
              <div className="absolute inset-y-0 left-0 w-1/3 animate-[slide_1.8s_ease-in-out_infinite] bg-white/60 rounded-full" />
            </div>
          </div>
        </div>
      )}

      {/* Forecaster Detail Modal */}
      {selectedForecaster && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedForecaster(null)}>
          <div className="relative w-full max-w-3xl bg-[#1a1f2e] border-4 border-[#2d3748] rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.75)] p-8 text-white max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setSelectedForecaster(null)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white text-2xl font-bold"
            >
              ×
            </button>
            
            {(() => {
              const classInfo = FORECASTER_CLASSES[selectedForecaster.forecaster_class as keyof typeof FORECASTER_CLASSES]
              return (
                <div>
                  <h2 className={`${pressStart.className} text-2xl tracking-[0.15em] uppercase mb-4 text-[#f7f5f0]`}>
                    {classInfo?.name || selectedForecaster.forecaster_class}
                  </h2>
                  
                  {/* Description */}
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-2 text-[#f7f5f0]">Description</h3>
                    <p className="text-gray-300 leading-relaxed">{classInfo?.description || "No description available"}</p>
                  </div>

                  {/* Traits */}
                  {classInfo?.traits && (
                    <div className="mb-6">
                      <h3 className="text-lg font-semibold mb-2 text-[#f7f5f0]">Traits</h3>
                      <ul className="list-disc list-inside space-y-1 text-gray-300">
                        {classInfo.traits.map((trait, idx) => (
                          <li key={idx} className="text-sm">{trait}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Prediction Results */}
                  {selectedForecaster.status === "completed" && (
                    <div className="mb-6 p-6 bg-[#0f172a]/50 rounded-lg border border-[#2d3748]">
                      <h3 className="text-lg font-semibold mb-4 text-[#f7f5f0]">Prediction</h3>
                      
                      {selectedForecaster.prediction_result && (
                        <div className="mb-4">
                          <div className="text-3xl font-bold text-[#f7f5f0] mb-2">
                            {selectedForecaster.prediction_result.prediction}
                          </div>
                        </div>
                      )}
                      
                      <div className="grid grid-cols-2 gap-4">
                        {selectedForecaster.prediction_probability !== undefined && (
                          <div>
                            <div className="text-sm text-gray-400 mb-1">Probability</div>
                            <div className={`${pressStart.className} text-3xl tracking-[0.1em] text-[#2d7dd2]`}>
                              {Math.round(selectedForecaster.prediction_probability * 100)}%
                            </div>
                          </div>
                        )}
                        {selectedForecaster.confidence !== undefined && (
                          <div>
                            <div className="text-sm text-gray-400 mb-1">Confidence</div>
                            <div className={`${pressStart.className} text-3xl tracking-[0.1em] text-[#60a5fa]`}>
                              {Math.round(selectedForecaster.confidence * 100)}%
                            </div>
                          </div>
                        )}
                      </div>

                      {selectedForecaster.prediction_result?.reasoning && (
                        <div className="mt-4 pt-4 border-t border-[#2d3748]">
                          <div className="text-sm text-gray-400 mb-2">Reasoning</div>
                          <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                            {selectedForecaster.prediction_result.reasoning}
                          </p>
                        </div>
                      )}

                      {selectedForecaster.prediction_result?.key_factors && selectedForecaster.prediction_result.key_factors.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-[#2d3748]">
                          <div className="text-sm text-gray-400 mb-2">Key Factors</div>
                          <ul className="list-disc list-inside space-y-1">
                            {selectedForecaster.prediction_result.key_factors.map((factor, idx) => (
                              <li key={idx} className="text-sm text-gray-300">{factor}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {selectedForecaster.status === "running" && (
                    <div className="p-6 bg-yellow-900/25 rounded-lg border border-yellow-500/30">
                      <p className="text-yellow-200">This forecaster is still analyzing...</p>
                    </div>
                  )}

                  {selectedForecaster.status === "failed" && (
                    <div className="p-6 bg-red-900/25 rounded-lg border border-red-500/30">
                      <p className="text-red-200">This forecaster encountered an error.</p>
                      {selectedForecaster.error_message && (
                        <p className="text-red-300 text-sm mt-2">{selectedForecaster.error_message}</p>
                      )}
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        </div>
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
      <div className="h-screen w-full flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    }>
      <OfficePageContent />
    </Suspense>
  )
}

