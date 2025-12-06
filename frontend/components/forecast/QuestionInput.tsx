"use client"

import { useState } from "react"

interface QuestionInputProps {
  onSubmit: (questionText: string, questionType: string) => void
  isSubmitting: boolean
}

export function QuestionInput({ onSubmit, isSubmitting }: QuestionInputProps) {
  const [questionText, setQuestionText] = useState("")
  const [questionType, setQuestionType] = useState("binary")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (questionText.trim()) {
      onSubmit(questionText, questionType)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
          Forecasting Question
        </label>
        <textarea
          id="question"
          value={questionText}
          onChange={(e) => setQuestionText(e.target.value)}
          placeholder="e.g., Will Bitcoin reach $150,000 by December 31, 2025?"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          rows={4}
          required
          disabled={isSubmitting}
        />
      </div>

      <div>
        <label htmlFor="type" className="block text-sm font-medium text-gray-700 mb-2">
          Question Type
        </label>
        <select
          id="type"
          value={questionType}
          onChange={(e) => setQuestionType(e.target.value)}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          disabled={isSubmitting}
        >
          <option value="binary">Binary (Yes/No)</option>
          <option value="numeric">Numeric Range</option>
          <option value="categorical">Categorical</option>
        </select>
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !questionText.trim()}
        className="w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        {isSubmitting ? "Creating Forecast..." : "Start Forecasting"}
      </button>
    </form>
  )
}
