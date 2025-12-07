"use client"

interface ConfidenceGaugeProps {
  confidence: number // 0-1
  label?: string // Optional label (default: "Confidence Score")
  showDescriptor?: boolean // Toggle the bottom descriptor text
}

export function ConfidenceGauge({ confidence, label = "Confidence Score", showDescriptor = true }: ConfidenceGaugeProps) {
  const percentage = Math.round(confidence * 100)

  const getColor = (conf: number) => {
    if (conf >= 0.8) return "text-green-600 bg-green-100"
    if (conf >= 0.6) return "text-blue-600 bg-blue-100"
    if (conf >= 0.4) return "text-yellow-600 bg-yellow-100"
    return "text-red-600 bg-red-100"
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className={`text-2xl font-bold ${getColor(confidence).split(' ')[0]}`}>
          {percentage}%
        </span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
        <div
          className={`h-full ${getColor(confidence).split(' ')[1]} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {showDescriptor && (
        <p className="text-xs text-gray-500 text-center">
          {confidence >= 0.8 && "High confidence"}
          {confidence >= 0.6 && confidence < 0.8 && "Moderate confidence"}
          {confidence >= 0.4 && confidence < 0.6 && "Low confidence"}
          {confidence < 0.4 && "Very low confidence"}
        </p>
      )}
    </div>
  )
}
