"use client"

import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"
import { AgentLog } from "@/types/agent"
import { Factor } from "@/types/forecast"

interface RealtimeData {
  agentLogs: AgentLog[]
  factors: Factor[]
  sessionStatus: string | null
  currentPhase: string | null
}

export function useRealtimeAgents(sessionId: string) {
  const [data, setData] = useState<RealtimeData>({
    agentLogs: [],
    factors: [],
    sessionStatus: null,
    currentPhase: null,
  })

  useEffect(() => {
    if (!sessionId) return

    const channel = supabase
      .channel(`session:${sessionId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "agent_logs",
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => {
          setData((prev) => ({
            ...prev,
            agentLogs: [...prev.agentLogs, payload.new as AgentLog],
          }))
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "agent_logs",
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => {
          setData((prev) => ({
            ...prev,
            agentLogs: prev.agentLogs.map((log) =>
              log.id === payload.new.id ? (payload.new as AgentLog) : log
            ),
          }))
        }
      )
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "factors",
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => {
          setData((prev) => ({
            ...prev,
            factors: [...prev.factors, payload.new as Factor],
          }))
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "sessions",
          filter: `id=eq.${sessionId}`,
        },
        (payload) => {
          setData((prev) => ({
            ...prev,
            sessionStatus: payload.new.status,
            currentPhase: payload.new.current_phase,
          }))
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [sessionId])

  return data
}
