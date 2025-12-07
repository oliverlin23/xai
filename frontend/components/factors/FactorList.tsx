"use client"

import { Factor } from "@/types/forecast"
import { FactorImportance } from "./FactorImportance"

interface FactorListProps {
  factors: Factor[]
}

export function FactorList({ factors }: FactorListProps) {
  const formatText = (text: string) =>
    text
      .split(/\n+/)
      .map((line) => line.trim().replace(/^#+\s*/, "").replace(/^[-*]\s*/, "").replace(/^\d+\.\s*/, ""))
      .filter(Boolean)

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Discovered Factors ({factors.length})
      </h2>

      {factors.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          No factors discovered yet...
        </p>
      ) : (
        <div className="space-y-4">
          {factors
            .sort((a, b) => (b.importance_score || 0) - (a.importance_score || 0))
            .map((factor) => (
              <div
                key={factor.id}
                className="border border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-900">{factor.name}</h3>
                  {factor.importance_score && (
                    <FactorImportance score={factor.importance_score} />
                  )}
                </div>

                {factor.category && (
                  <span className="inline-block px-2 py-1 bg-indigo-100 text-indigo-700 text-xs rounded mb-2">
                    {factor.category}
                  </span>
                )}

                {factor.description && (
                  <div className="text-sm font-mono text-gray-800 leading-6 whitespace-pre-wrap mb-2 bg-gray-50 border border-gray-200 rounded px-3 py-2">
                    {(() => {
                      const lines = formatText(factor.description)
                      return lines.length ? lines.join(" ") : factor.description
                    })()}
                  </div>
                )}

                {factor.research_summary && (
                  <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded text-sm text-gray-800 font-mono leading-6 whitespace-pre-wrap">
                    <strong className="block mb-2 font-sans text-gray-900">Research Summary:</strong>
                    {(() => {
                      const lines = formatText(factor.research_summary)
                      return lines.length ? lines.join(" ") : factor.research_summary
                    })()}
                  </div>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  )
}

