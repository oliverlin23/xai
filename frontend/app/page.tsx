"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { QuestionInput } from "@/components/forecast/QuestionInput"

export default function HomePage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (
    questionText: string,
    questionType: string,
    agentCounts?: { phase_1_discovery: number; phase_2_validation: number; phase_3_research: number; phase_4_synthesis: number }
  ) => {
    setIsSubmitting(true)

    try {
      const requestBody: any = {
        question_text: questionText,
        question_type: questionType,
      }
      
      // Add agent_counts if provided
      if (agentCounts) {
        requestBody.agent_counts = agentCounts
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/forecasts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error("Failed to create forecast")
      }

      const data = await response.json()
      router.push(`/forecast/${data.id}`)
    } catch (error) {
      console.error("Error creating forecast:", error)
      alert("Failed to create forecast. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          AI-Powered Superforecasting
        </h1>
        <p className="text-xl text-gray-600">
          24 collaborative AI agents analyze your question to produce calibrated predictions
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
            10 agents discover diverse factors influencing your question
          </p>
        </div>
        <div className="bg-white rounded-lg p-6 shadow">
          <div className="text-3xl mb-2">📊</div>
          <h3 className="font-bold text-lg mb-2">Deep Research</h3>
          <p className="text-gray-600 text-sm">
            10 agents research historical patterns and current data
          </p>
        </div>
        <div className="bg-white rounded-lg p-6 shadow">
          <div className="text-3xl mb-2">🎯</div>
          <h3 className="font-bold text-lg mb-2">Synthesis</h3>
          <p className="text-gray-600 text-sm">
            Expert synthesizer produces calibrated predictions with confidence scores
          </p>
        </div>
      </div>
    </div>
  )
}
