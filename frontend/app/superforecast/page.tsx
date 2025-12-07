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
    <div className="max-w-4xl mx-auto py-12 px-4 pt-24">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          AI-Powered Superforecasting
        </h1>
        <p className="text-xl text-gray-600">
          23 collaborative AI agents analyze your question to produce calibrated predictions
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-lg p-8">
        <QuestionInput onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </div>

      <div className="mt-12 grid md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg p-6 shadow">
          <div className="text-3xl mb-2">🔍</div>
          <h3 className="font-bold text-lg mb-2">Factor Discovery</h3>
          <p className="text-gray-600 text-sm">
            Multiple agents discover diverse factors influencing your question
          </p>
        </div>
        <div className="bg-white rounded-lg p-6 shadow">
          <div className="text-3xl mb-2">✅</div>
          <h3 className="font-bold text-lg mb-2">Validation</h3>
          <p className="text-gray-600 text-sm">
            Agents validate and rate factors for importance
          </p>
        </div>
        <div className="bg-white rounded-lg p-6 shadow">
          <div className="text-3xl mb-2">📊</div>
          <h3 className="font-bold text-lg mb-2">Deep Research</h3>
          <p className="text-gray-600 text-sm">
            Agents research historical patterns and current data
          </p>
        </div>
      </div>
    </div>
  )
}

