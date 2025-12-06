"use client"

import Link from "next/link"
import { useForecastList } from "@/hooks/useForecast"
import { ConfidenceGauge } from "@/components/forecast/ConfidenceGauge"

export default function HistoryPage() {
  const { data, isLoading, error } = useForecastList()

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading forecasts...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <p className="text-red-600">Error loading forecast history</p>
        </div>
      </div>
    )
  }

  const forecasts = data?.forecasts || []

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">
          Forecast History
        </h1>
        <Link
          href="/"
          className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700"
        >
          New Forecast
        </Link>
      </div>

      {forecasts.length === 0 ? (
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <p className="text-gray-600 mb-4">No forecasts yet</p>
          <Link
            href="/"
            className="text-indigo-600 hover:text-indigo-800 font-medium"
          >
            Create your first forecast →
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {forecasts.map((forecast: any) => (
            <Link
              key={forecast.id}
              href={
                forecast.status === "completed"
                  ? `/forecast/${forecast.id}/result`
                  : `/forecast/${forecast.id}`
              }
              className="block"
            >
              <div className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {forecast.question_text}
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span>
                        {new Date(forecast.created_at).toLocaleDateString()}
                      </span>
                      <span className="capitalize">
                        {forecast.question_type}
                      </span>
                      <span
                        className={`px-2 py-1 rounded ${
                          forecast.status === "completed"
                            ? "bg-green-100 text-green-800"
                            : forecast.status === "running"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {forecast.status}
                      </span>
                    </div>

                    {forecast.prediction_result && (
                      <div className="mt-4">
                        <p className="text-gray-700 font-medium mb-2">
                          {forecast.prediction_result.prediction}
                        </p>
                        <div className="max-w-md">
                          <ConfidenceGauge
                            confidence={forecast.prediction_result.confidence}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="text-right text-sm text-gray-500">
                    <div>{forecast.factors?.length || 0} factors</div>
                    <div>{forecast.total_cost_tokens.toLocaleString()} tokens</div>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
