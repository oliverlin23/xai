export type TraderType = "fundamental" | "noise" | "user"

export interface TraderProfile {
  session_id: string
  trader_type: TraderType
  name: string
  display_name: string
  description: string
  role: string
  position: number
  cash: number
  pnl: number
  system_prompt?: string
}

