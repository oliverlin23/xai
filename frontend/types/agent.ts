// Office UI Agent interface
export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'working' | 'resting' | 'break';
  cubicleId: number; // Maps to a specific desk position
  sentiment: number; // -1 to 1
  currentAction?: string;
}

// Forecasting UI AgentLog interface
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
  web_search_sources?: number
  web_search_used?: boolean
}

export interface MarketSignal {
  timestamp: number;
  data: any;
}

