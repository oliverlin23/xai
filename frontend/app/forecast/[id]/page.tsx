"use client"

import { useParams, useRouter } from "next/navigation"
import { useEffect } from "react"
import { useForecast } from "@/hooks/useForecast"
import { useRealtimeAgents } from "@/hooks/useRealtimeAgents"
import { AgentTimeline } from "@/components/agents/AgentTimeline"
import { AgentMonitor } from "@/components/agents/AgentMonitor"
import { FactorList } from "@/components/factors/FactorList"

export default function ForecastMonitorPage() {
  const params = useParams()
  const router = useRouter()
  const forecastId = params.id as string

  const { data: forecast, isLoading, error } = useForecast(forecastId)
  const realtimeData = useRealtimeAgents(forecastId)

  // Redirect to result page when completed
  useEffect(() => {
    if (forecast?.status === "completed") {
      router.push(`/forecast/${forecastId}/result`)
    }
  }, [forecast?.status, forecastId, router])

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading forecast...</p>
        </div>
      </div>
    )
  }

  if (error || !forecast) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <p className="text-red-600">Error loading forecast</p>
        </div>
      </div>
    )
  }

  // Deduplicate agent logs by ID (realtime updates may duplicate initial fetch)
  const agentLogsMap = new Map<string, typeof forecast.agent_logs[0]>()
  forecast.agent_logs.forEach((log: any) => agentLogsMap.set(log.id, log))
  realtimeData.agentLogs.forEach((log: any) => agentLogsMap.set(log.id, log))
  const agentLogs = Array.from(agentLogsMap.values())
  
  // Deduplicate factors by ID
  const factorsMap = new Map<string, typeof forecast.factors[0]>()
  forecast.factors.forEach((factor: any) => factorsMap.set(factor.id, factor))
  realtimeData.factors.forEach((factor: any) => factorsMap.set(factor.id, factor))
  const factors = Array.from(factorsMap.values())
  const currentPhase = realtimeData.currentPhase || forecast.current_phase || "factor_discovery"
  const status = realtimeData.sessionStatus || forecast.status

  return (
    <div className="max-w-7xl mx-auto px-4 pt-24 pb-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">
          Analyzing Your Question
        </h1>
        <p className="text-lg text-gray-700 leading-relaxed">
          {forecast.question_text}
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-1">
          <AgentTimeline currentPhase={currentPhase} status={status} agentLogs={agentLogs} />
        </div>

        <div className="lg:col-span-2 space-y-6">
          <AgentMonitor agentLogs={agentLogs} currentPhase={currentPhase} />

          {factors.length > 0 && (
            <FactorList factors={factors} />
          )}
        </div>
      </div>
    </div>
  )
}
