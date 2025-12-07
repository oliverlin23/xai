"use client"

import { ConfidenceGauge } from "./ConfidenceGauge"

interface ForecastCardProps {
  prediction: string
  prediction_probability: number  // Probability of the event (0.0-1.0)
  confidence: number  // Confidence in the probability estimate (0.0-1.0)
  reasoning: string
  keyFactors: string[]
  showReasoning?: boolean
  showKeyFactors?: boolean
}

export function ForecastCard({
  prediction,
  prediction_probability,
  confidence,
  reasoning,
  keyFactors,
  showReasoning = true,
  showKeyFactors = true,
}: ForecastCardProps) {
  // Fallback to confidence for backward compatibility if prediction_probability not provided
  const probability = prediction_probability !== undefined ? prediction_probability : confidence

  // Light formatting cleanup for markdown-ish strings (reasoning, factors)
  const formatReasoning = (text: string) => {
    return text
      .split(/\n+/)
      .map((line) => line.trim().replace(/^#+\s*/, "").replace(/^[-*]\s*/, "").replace(/^\d+\.\s*/, ""))
      .filter(Boolean)
  }
  const reasoningLines = formatReasoning(reasoning || "")
  
  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Final Prediction</h2>

      <div className="mb-8">
        <div className="text-3xl font-bold text-indigo-600 mb-4">
          {prediction}
        </div>
        <div className="mb-4">
          <ConfidenceGauge confidence={probability} label="Probability" showDescriptor={false} />
        </div>
        {prediction_probability !== undefined && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">Confidence in Probability Estimate</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full transition-all ${
                    confidence >= 0.8 ? 'bg-green-500' :
                    confidence >= 0.6 ? 'bg-yellow-500' :
                    confidence >= 0.4 ? 'bg-orange-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${confidence * 100}%` }}
                />
              </div>
              <span className="text-sm font-medium text-gray-700 w-12 text-right">
                {Math.round(confidence * 100)}%
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {confidence >= 0.8 && "High confidence - comprehensive research, authoritative sources"}
              {confidence >= 0.6 && confidence < 0.8 && "Moderate confidence - good research coverage"}
              {confidence >= 0.4 && confidence < 0.6 && "Low confidence - limited research or mixed sources"}
              {confidence < 0.4 && "Very low confidence - minimal reliable evidence"}
            </div>
          </div>
        )}
      </div>

      {showReasoning && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Reasoning</h3>
          <div className="space-y-2 font-mono text-[13px] md:text-sm text-gray-800 leading-6 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 whitespace-pre-wrap">
            {reasoningLines.length === 0 ? (
              <p className="font-sans italic text-gray-500">No reasoning provided.</p>
            ) : (
              reasoningLines.map((line, idx) => (
                <p key={idx}>
                  {line}
                </p>
              ))
            )}
          </div>
        </div>
      )}

      {showKeyFactors && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Key Factors</h3>
          <div className="space-y-2">
            {keyFactors.map((factor, index) => {
              const lines = formatReasoning(factor)
              const rendered = lines.length > 0 ? lines.join(" ") : factor
              return (
                <div key={index} className="flex items-start">
                  <span className="text-indigo-600 mr-2">•</span>
                  <span className="text-gray-800/90 text-sm md:text-base leading-7">
                    {rendered}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
