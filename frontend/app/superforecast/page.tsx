"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { QuestionInput } from "@/components/forecast/QuestionInput"
import { api } from "@/lib/api"

export default function SuperforecastPage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)

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

  return (
    <div
      className="min-h-screen bg-cover bg-center bg-fixed"
      style={{ backgroundImage: 'url("/groklogo.png")' }}
    >
      <div className="min-h-screen bg-slate-600/35 overflow-y-auto flex items-center justify-center px-4 py-24">
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
    </div>
  )
}

