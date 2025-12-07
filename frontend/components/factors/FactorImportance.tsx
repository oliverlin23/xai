"use client"

interface FactorImportanceProps {
  score: number // 0-10
}

export function FactorImportance({ score }: FactorImportanceProps) {
  const getColor = (s: number) => {
    if (s >= 8) return "bg-red-500"
    if (s >= 6) return "bg-orange-500"
    if (s >= 4) return "bg-yellow-500"
    return "bg-gray-400"
  }

  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-0.5">
        {[...Array(10)].map((_, i) => (
          <div
            key={i}
            className={`w-2 h-6 rounded-sm ${
              i < score ? getColor(score) : "bg-gray-200"
            }`}
          />
        ))}
      </div>
      <span className="text-sm font-medium text-gray-700">
        {score.toFixed(1)}
      </span>
    </div>
  )
}

