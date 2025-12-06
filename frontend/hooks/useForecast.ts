"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export function useForecast(forecastId: string) {
  return useQuery({
    queryKey: ["forecast", forecastId],
    queryFn: () => api.forecasts.get(forecastId),
    refetchInterval: (data: any) => {
      // Stop polling if forecast is completed or failed
      if (data?.status === "completed" || data?.status === "failed") {
        return false
      }
      // Poll every 2 seconds while running
      return 2000
    },
  })
}

export function useForecastList() {
  return useQuery({
    queryKey: ["forecasts"],
    queryFn: () => api.forecasts.list(),
  })
}
