/**
 * Database types for Supabase
 * This helps with TypeScript type checking for Supabase queries
 */
export type Database = {
  public: {
    Tables: {
      sessions: {
        Row: {
          id: string
          question_text: string
          question_type: string
          status: string
          current_phase: string | null
          created_at: string
          started_at: string | null
          completed_at: string | null
          prediction_result: any | null
          total_cost_tokens: number
        }
        Insert: {
          id?: string
          question_text: string
          question_type: string
          status?: string
          current_phase?: string | null
          created_at?: string
          started_at?: string | null
          completed_at?: string | null
          prediction_result?: any | null
          total_cost_tokens?: number
        }
        Update: {
          id?: string
          question_text?: string
          question_type?: string
          status?: string
          current_phase?: string | null
          created_at?: string
          started_at?: string | null
          completed_at?: string | null
          prediction_result?: any | null
          total_cost_tokens?: number
        }
      }
      agent_logs: {
        Row: {
          id: string
          session_id: string
          agent_name: string
          phase: string
          status: string
          output_data: any | null
          error_message: string | null
          tokens_used: number
          created_at: string
          completed_at: string | null
        }
        Insert: {
          id?: string
          session_id: string
          agent_name: string
          phase: string
          status?: string
          output_data?: any | null
          error_message?: string | null
          tokens_used?: number
          created_at?: string
          completed_at?: string | null
        }
        Update: {
          id?: string
          session_id?: string
          agent_name?: string
          phase?: string
          status?: string
          output_data?: any | null
          error_message?: string | null
          tokens_used?: number
          created_at?: string
          completed_at?: string | null
        }
      }
      factors: {
        Row: {
          id: string
          session_id: string
          name: string
          description: string | null
          category: string | null
          importance_score: number | null
          research_summary: string | null
          created_at: string
        }
        Insert: {
          id?: string
          session_id: string
          name: string
          description?: string | null
          category?: string | null
          importance_score?: number | null
          research_summary?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          session_id?: string
          name?: string
          description?: string | null
          category?: string | null
          importance_score?: number | null
          research_summary?: string | null
          created_at?: string
        }
      }
      orderbook_live: {
        Row: {
          id: string
          session_id: string
          trader_name: string
          side: "buy" | "sell"
          price: number
          quantity: number
          filled_quantity: number
          status: "open" | "filled" | "partially_filled" | "cancelled"
          created_at: string
        }
        Insert: {
          id?: string
          session_id: string
          trader_name: string
          side: "buy" | "sell"
          price: number
          quantity?: number
          filled_quantity?: number
          status?: "open" | "filled" | "partially_filled" | "cancelled"
          created_at?: string
        }
        Update: {
          id?: string
          session_id?: string
          trader_name?: string
          side?: "buy" | "sell"
          price?: number
          quantity?: number
          filled_quantity?: number
          status?: "open" | "filled" | "partially_filled" | "cancelled"
          created_at?: string
        }
      }
      trades: {
        Row: {
          id: string
          session_id: string
          buyer_name: string
          seller_name: string
          price: number
          quantity: number
          created_at: string
        }
        Insert: {
          id?: string
          session_id: string
          buyer_name: string
          seller_name: string
          price: number
          quantity: number
          created_at?: string
        }
        Update: {
          id?: string
          session_id?: string
          buyer_name?: string
          seller_name?: string
          price?: number
          quantity?: number
          created_at?: string
        }
      }
      trader_state_live: {
        Row: {
          id: string
          session_id: string
          trader_type: "fundamental" | "noise" | "user"
          name: string
          system_prompt: string | null
          position: number
          cash: number
          pnl: number
          updated_at: string
        }
        Insert: {
          id?: string
          session_id: string
          trader_type: "fundamental" | "noise" | "user"
          name: string
          system_prompt?: string | null
          position?: number
          cash?: number
          pnl?: number
          updated_at?: string
        }
        Update: {
          id?: string
          session_id?: string
          trader_type?: "fundamental" | "noise" | "user"
          name?: string
          system_prompt?: string | null
          position?: number
          cash?: number
          pnl?: number
          updated_at?: string
        }
      }
    }
  }
}

