"use client"

import { AgentLog } from "@/types/agent"
import { AgentCard } from "./AgentCard"

interface AgentMonitorProps {
  agentLogs: AgentLog[]
  currentPhase: string
}

export function AgentMonitor({ agentLogs, currentPhase }: AgentMonitorProps) {
  const phaseAgents = agentLogs.filter(log => currentPhase === "all" || log.phase === currentPhase)

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Agent Activity {currentPhase !== "all" && `- ${currentPhase.replace(/_/g, " ").toUpperCase()}`}
      </h2>

      <div className="space-y-3">
        {phaseAgents.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No agents running yet...
          </p>
        ) : (
          phaseAgents.map((log) => (
            <AgentCard key={log.id} agentLog={log} />
          ))
        )}
      </div>
    </div>
  )
}

