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
          setData((prev) => {
            const newLog = payload.new as AgentLog
            // Check if log already exists (avoid duplicates)
            const exists = prev.agentLogs.some(log => log.id === newLog.id)
            if (exists) {
              return prev
            }
            return {
              ...prev,
              agentLogs: [...prev.agentLogs, newLog],
            }
          })
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
          setData((prev) => {
            const newFactor = payload.new as Factor
            // Check if factor already exists (avoid duplicates)
            const exists = prev.factors.some(factor => factor.id === newFactor.id)
            if (exists) {
              return prev
            }
            return {
              ...prev,
              factors: [...prev.factors, newFactor],
            }
          })
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
