export interface Factor {
  id: string
  session_id: string
  name: string
  description?: string
  category?: string
  importance_score?: number
  research_summary?: string
  created_at: string
}

export interface PredictionResult {
  prediction: string
  prediction_probability: number  // Probability of the event occurring (0.0-1.0)
  confidence: number  // Confidence in the probability estimate, based on evidence quality (0.0-1.0)
  reasoning: string
  key_factors: string[]
  total_duration_seconds?: number
  total_duration_formatted?: string
  phase_durations?: {
    phase_1_discovery: number
    phase_2_validation: number
    phase_3_research: number
    phase_4_synthesis: number
  }
}

export interface ForecasterResponse {
  id: string
  session_id: string
  forecaster_class: string
  prediction_result?: PredictionResult
  prediction_probability?: number
  confidence?: number
  total_duration_seconds?: number
  total_duration_formatted?: string
  phase_durations?: {
    phase_1_discovery: number
    phase_2_validation: number
    phase_3_research: number
    phase_4_synthesis: number
  }
  status: "running" | "completed" | "failed"
  error_message?: string
  created_at: string
  completed_at?: string
}

export interface Forecast {
  id: string
  question_text: string
  question_type: string
  status: "running" | "completed" | "failed"
  current_phase?: string
  prediction_result?: PredictionResult
  forecaster_responses?: ForecasterResponse[]
  factors: Factor[]
  agent_logs: any[]
  total_cost_tokens: number
  created_at: string
  completed_at?: string
  total_duration_seconds?: number
  total_duration_formatted?: string
  phase_durations?: {
    phase_1_discovery: number
    phase_2_validation: number
    phase_3_research: number
    phase_4_synthesis: number
  }
}
