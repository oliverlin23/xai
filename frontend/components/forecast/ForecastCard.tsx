"use client"

import { ConfidenceGauge } from "./ConfidenceGauge"

interface ForecastCardProps {
  prediction: string
  confidence: number
  reasoning: string
  keyFactors: string[]
}

export function ForecastCard({ prediction, confidence, reasoning, keyFactors }: ForecastCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Final Prediction</h2>

      <div className="mb-8">
        <div className="text-3xl font-bold text-indigo-600 mb-4">
          {prediction}
        </div>
        <ConfidenceGauge confidence={confidence} />
      </div>

      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Reasoning</h3>
        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
          {reasoning}
        </p>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Key Factors</h3>
        <ul className="space-y-2">
          {keyFactors.map((factor, index) => (
            <li key={index} className="flex items-start">
              <span className="text-indigo-600 mr-2">•</span>
              <span className="text-gray-700">{factor}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
