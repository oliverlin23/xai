"use client"

import { useParams } from "next/navigation"
import Link from "next/link"
import { useForecast } from "@/hooks/useForecast"
import { ForecastCard } from "@/components/forecast/ForecastCard"
import { FactorList } from "@/components/factors/FactorList"
import { AgentMonitor } from "@/components/agents/AgentMonitor"

export default function ForecastResultPage() {
  const params = useParams()
  const forecastId = params.id as string

  const { data: forecast, isLoading, error } = useForecast(forecastId)

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading results...</p>
        </div>
      </div>
    )
  }

  if (error || !forecast) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <p className="text-red-600">Error loading forecast results</p>
        </div>
      </div>
    )
  }

  if (forecast.status !== "completed" || !forecast.prediction_result) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <p className="text-gray-600">Forecast not yet completed</p>
          <Link
            href={`/forecast/${forecastId}`}
            className="text-indigo-600 hover:text-indigo-800 mt-4 inline-block"
          >
            ← Back to monitor
          </Link>
        </div>
      </div>
    )
  }

  const agentTokenTotal = forecast.agent_logs.reduce((sum: number, log: any) => {
    const tokens = Number(log.tokens_used ?? 0)
    return sum + (Number.isFinite(tokens) ? tokens : 0)
  }, 0)

  const parsedTotalCost = Number(forecast.total_cost_tokens)
  const totalTokens =
    Number.isFinite(parsedTotalCost) && parsedTotalCost > 0 ? parsedTotalCost : agentTokenTotal

  const formattedReasoning = forecast.prediction_result?.reasoning || ""
  const keyFactors = forecast.prediction_result?.key_factors || []

  return (
    <div className="max-w-7xl mx-auto px-4 pt-24 pb-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Forecast Results
          </h1>
          <p className="text-lg text-gray-600">
            {forecast.question_text}
          </p>
        </div>
        <Link
          href="/"
          className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700"
        >
          New Forecast
        </Link>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-8 items-stretch">
        <div className="lg:col-span-2 h-full">
          <ForecastCard
            prediction={forecast.prediction_result.prediction}
            prediction_probability={forecast.prediction_result.prediction_probability}
            confidence={forecast.prediction_result.confidence}
            reasoning={formattedReasoning}
            keyFactors={keyFactors}
            showReasoning={false}
            showKeyFactors={false}
          />
        </div>

        <div className="h-full">
          <div className="bg-white rounded-lg shadow-lg p-6 h-full flex flex-col">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Forecast Statistics
            </h3>
            <div className="space-y-3 text-sm flex-1">
              <div className="flex justify-between">
                <span className="text-gray-600">Total Agents</span>
                <span className="font-semibold">{forecast.agent_logs.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Factors Analyzed</span>
                <span className="font-semibold">{forecast.factors.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total Tokens Used</span>
                <span className="font-semibold">
                  {totalTokens.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Completed At</span>
                <span className="font-semibold text-xs">
                  {forecast.completed_at
                    ? new Date(forecast.completed_at).toLocaleString()
                    : "N/A"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Reasoning</h3>
          <div className="font-mono text-[13px] md:text-sm text-gray-800 leading-6 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 whitespace-pre-wrap">
            {formattedReasoning.trim()
              ? formattedReasoning
              : <span className="font-sans italic text-gray-500">No reasoning provided.</span>}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Key Factors</h3>
          {keyFactors.length === 0 ? (
            <p className="italic text-gray-500">No key factors provided.</p>
          ) : (
            <ul className="space-y-2">
              {keyFactors.map((factor: string, index: number) => (
                <li key={index} className="flex items-start">
                  <span className="text-indigo-600 mr-2">•</span>
                  <span className="text-gray-800/90 text-sm md:text-base leading-7">
                    {factor}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Discovered Factors</h3>
          <FactorList factors={forecast.factors} />
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Agent Activity</h3>
          <AgentMonitor agentLogs={forecast.agent_logs} currentPhase="all" />
        </div>
      </div>
    </div>
  )
}
