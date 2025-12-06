export interface AgentLog {
  id: string
  session_id: string
  agent_name: string
  phase: string
  status: "running" | "completed" | "failed"
  output_data?: Record<string, any>
  error_message?: string
  tokens_used: number
  created_at: string
  completed_at?: string
}
