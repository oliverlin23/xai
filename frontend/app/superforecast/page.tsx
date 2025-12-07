"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { QuestionInput } from "@/components/forecast/QuestionInput"
import { api } from "@/lib/api"

export default function SuperforecastPage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [previousOpen, setPreviousOpen] = useState(false)
  const [previousLoading, setPreviousLoading] = useState(false)
  const [previousError, setPreviousError] = useState<string | null>(null)
  const [previousForecasts, setPreviousForecasts] = useState<Array<{
    id: string
    question_text: string
    status: string
    prediction_result?: { prediction?: string; prediction_probability?: number; confidence?: number }
    completed_at?: string
  }>>([])

  const handleSubmit = async (
    questionText: string,
    questionType: string,
    agentCounts?: { phase_1_discovery?: number; phase_2_validation?: number; phase_3_research?: number; phase_3_historical?: number; phase_3_current?: number; phase_4_synthesis?: number },
    forecasterClass?: string
  ) => {
    setIsSubmitting(true)

    try {
      const requestBody: any = {
        question_text: questionText,
        question_type: questionType,
      }
      
      // Add forecaster_class if provided
      if (forecasterClass) {
        requestBody.forecaster_class = forecasterClass
      }
      
      // Only send agent_counts if forecaster_class is "balanced" (or not set)
      // Other classes use their own optimized defaults
      if (agentCounts && (!forecasterClass || forecasterClass === "balanced")) {
        requestBody.agent_counts = agentCounts
      }

      const data = await api.forecasts.create(requestBody)
      router.push(`/forecast/${data.id}`)
    } catch (error) {
      console.error("Error creating forecast:", error)
      alert("Failed to create forecast. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  useEffect(() => {
    if (!previousOpen) return
    const load = async () => {
      setPreviousLoading(true)
      setPreviousError(null)
      try {
        const res = await api.forecasts.list(10, 0)
        setPreviousForecasts(res?.forecasts ?? [])
      } catch (err: any) {
        setPreviousError(err?.message || "Failed to load previous forecasts")
      } finally {
        setPreviousLoading(false)
      }
    }
    load()
  }, [previousOpen])

  return (
    <div
      className="min-h-screen bg-cover bg-center bg-fixed"
      style={{ backgroundImage: 'url("/groklogo.png")' }}
    >
      <div className="relative min-h-screen bg-slate-600/35 overflow-y-auto flex items-center justify-center px-4 py-24">
        <button
          onClick={() => setPreviousOpen(true)}
          className="fixed top-6 right-6 z-50 px-4 py-2 rounded-lg border border-white/40 bg-white/20 text-white backdrop-blur shadow hover:bg-white/30 transition-colors text-sm"
        >
          Show Previous Forecasts
        </button>

        <div className="w-full max-w-4xl text-slate-900">
          <div
            className="bg-white text-[#0f172a] rounded-xl border-4 border-[#2d3748] shadow-[0_20px_50px_rgba(0,0,0,0.35)] p-8"
            style={{
              backgroundImage: `
                linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0) 40%),
                linear-gradient(90deg, rgba(248,249,251,0.96) 0%, rgba(242,245,249,0.96) 100%),
                repeating-linear-gradient(0deg, rgba(255,255,255,0.04), rgba(255,255,255,0.04) 4px, rgba(0,0,0,0.02) 4px, rgba(0,0,0,0.02) 8px)
              `,
            }}
          >
            <div className="text-center mb-6">
              <h1 className="text-3xl font-bold mb-2 text-[#0b1220]">
                Grok-Powered Superforecasting
              </h1>
              <p className="text-base text-slate-800">
                23 collaborative Grok agents analyze your question to produce calibrated predictions
              </p>
            </div>
            <QuestionInput onSubmit={handleSubmit} isSubmitting={isSubmitting} />
          </div>
        </div>
      </div>

      {previousOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setPreviousOpen(false)} />
          <div className="relative w-full max-w-4xl bg-white rounded-xl shadow-2xl p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-gray-900">Previous Forecasts</h3>
              <button
                onClick={() => setPreviousOpen(false)}
                className="text-gray-500 hover:text-gray-800 text-lg font-semibold"
              >
                ×
              </button>
            </div>

            {previousLoading && (
              <div className="text-center py-10 text-gray-600">Loading...</div>
            )}

            {previousError && (
              <div className="text-red-600 text-sm mb-3">{previousError}</div>
            )}

            {!previousLoading && !previousError && previousForecasts.length === 0 && (
              <div className="text-center py-10 text-gray-500">No previous forecasts found.</div>
            )}

            <div className="grid md:grid-cols-2 gap-4">
              {previousForecasts.map((item) => {
                const pred = item.prediction_result
                const probability = pred?.prediction_probability
                const confidence = pred?.confidence
                return (
                  <Link
                    key={item.id}
                    href={`/forecast/${item.id}/result`}
                    className="block border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-white"
                    onClick={() => setPreviousOpen(false)}
                  >
                    <div className="text-sm text-gray-500 mb-1">
                      {item.completed_at ? new Date(item.completed_at).toLocaleString() : "In progress"}
                    </div>
                    <div className="font-semibold text-gray-900 line-clamp-2 mb-2">
                      {item.question_text || "Untitled question"}
                    </div>
                    {pred?.prediction && (
                      <div className="text-indigo-700 font-semibold mb-1">
                        {pred.prediction}
                      </div>
                    )}
                    <div className="text-sm text-gray-700 flex flex-wrap gap-3">
                      {typeof probability === "number" && (
                        <span className="px-2 py-1 rounded bg-indigo-50 text-indigo-700 text-xs font-semibold">
                          Prob: {Math.round(probability * 100)}%
                        </span>
                      )}
                      {typeof confidence === "number" && (
                        <span className="px-2 py-1 rounded bg-slate-100 text-slate-700 text-xs font-semibold">
                          Conf: {Math.round(confidence * 100)}%
                        </span>
                      )}
                      <span className="px-2 py-1 rounded bg-gray-100 text-gray-700 text-xs font-semibold capitalize">
                        {item.status || "unknown"}
                      </span>
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

