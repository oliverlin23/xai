const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface CreateForecastParams {
  question_text: string
  question_type?: string
  agent_counts?: {
    phase_1_discovery?: number
    phase_2_validation?: number
    phase_3_research?: number
    phase_3_historical?: number
    phase_3_current?: number
    phase_4_synthesis?: number
  }
  forecaster_class?: string
  run_all_forecasters?: boolean
}

interface RunSessionParams {
  question_text: string
  question_type?: string
  resolution_criteria?: string
  resolution_date?: string
  trading_interval_seconds?: number
  agent_counts?: {
    phase_1_discovery?: number
    phase_2_validation?: number
    phase_3_research?: number
    phase_3_historical?: number
    phase_3_current?: number
    phase_4_synthesis?: number
  }
}

export const api = {
  forecasts: {
    create: async (params: CreateForecastParams) => {
      const response = await fetch(`${API_BASE}/api/forecasts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      })
      if (!response.ok) throw new Error("Failed to create forecast")
      return response.json()
    },

    get: async (id: string) => {
      const response = await fetch(`${API_BASE}/api/forecasts/${id}`)
      if (!response.ok) throw new Error("Failed to get forecast")
      return response.json()
    },

    list: async (limit = 10, offset = 0, questionText?: string) => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      })
      if (questionText) {
        params.append("question_text", questionText)
      }
      const response = await fetch(`${API_BASE}/api/forecasts?${params}`)
      if (!response.ok) throw new Error("Failed to list forecasts")
      return response.json()
    },
  },

  sessions: {
    /**
     * Start a new trading simulation session.
     * This runs superforecasters first, then starts 18 trading agents.
     * Returns immediately - simulation runs in background.
     */
    run: async (params: RunSessionParams) => {
      const response = await fetch(`${API_BASE}/api/sessions/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      })
      if (!response.ok) throw new Error("Failed to start session")
      return response.json()
    },

    /**
     * Get simulation status for a session.
     */
    getStatus: async (sessionId: string) => {
      const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/status`)
      if (!response.ok) throw new Error("Failed to get session status")
      return response.json()
    },

    /**
     * Stop a running trading simulation.
     */
    stop: async (sessionId: string) => {
      const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/stop`, {
        method: "POST",
      })
      if (!response.ok) throw new Error("Failed to stop session")
      return response.json()
    },
  },

  health: async () => {
    const response = await fetch(`${API_BASE}/health`)
    if (!response.ok) throw new Error("API health check failed")
    return response.json()
  },
}
