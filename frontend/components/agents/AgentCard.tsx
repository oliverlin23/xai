"use client"

import { AgentLog } from "@/types/agent"
import { Search } from "lucide-react"

interface AgentCardProps {
  agentLog: AgentLog
}

export function AgentCard({ agentLog }: AgentCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800"
      case "running":
        return "bg-blue-100 text-blue-800"
      case "failed":
        return "bg-red-100 text-red-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return "✓"
      case "running":
        return "⟳"
      case "failed":
        return "✗"
      default:
        return "○"
    }
  }

  // Check if web search was used (from output_data metadata)
  const webSearchMetadata = agentLog.output_data?._web_search_metadata
  const webSearchSources = agentLog.web_search_sources ?? 
    webSearchMetadata?.sources_used ?? 
    null
  const webSearchUsed = agentLog.web_search_used ?? 
    webSearchMetadata?.web_search_enabled ?? 
    (agentLog.phase === "factor_discovery" || agentLog.phase === "research")

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl">
            {getStatusIcon(agentLog.status)}
          </span>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-gray-900">
                {agentLog.agent_name}
              </h3>
              {webSearchUsed && (
                <div className="flex items-center gap-1 text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded" title="Web search enabled">
                  <Search className="h-3 w-3" />
                  {typeof webSearchSources === "number" && webSearchSources > 0 ? (
                    <span>{webSearchSources} sources</span>
                  ) : (
                    <span>Search</span>
                  )}
                </div>
              )}
            </div>
            <p className="text-sm text-gray-500">
              {agentLog.tokens_used.toLocaleString()} tokens
            </p>
          </div>
        </div>

        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(agentLog.status)}`}>
          {agentLog.status}
        </span>
      </div>

      {agentLog.error_message && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {agentLog.error_message}
        </div>
      )}
    </div>
  )
}
