"use client"

interface AgentTimelineProps {
  currentPhase: string
  status: string
}

const phases = [
  { key: "factor_discovery", label: "Factor Discovery", agents: 10 },
  { key: "validation", label: "Validation", agents: 3 },
  { key: "research", label: "Research", agents: 10 },
  { key: "synthesis", label: "Synthesis", agents: 1 },
]

export function AgentTimeline({ currentPhase, status }: AgentTimelineProps) {
  const getCurrentPhaseIndex = () => {
    return phases.findIndex(p => p.key === currentPhase)
  }

  const currentIndex = getCurrentPhaseIndex()

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-6">Progress</h2>

      <div className="space-y-4">
        {phases.map((phase, index) => {
          const isActive = phase.key === currentPhase
          const isCompleted = index < currentIndex || (index === currentIndex && status === "completed")
          const isPending = index > currentIndex

          return (
            <div key={phase.key} className="flex items-center gap-4">
              <div className="flex-shrink-0">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                    isCompleted
                      ? "bg-green-500 text-white"
                      : isActive
                      ? "bg-indigo-500 text-white animate-pulse"
                      : "bg-gray-200 text-gray-500"
                  }`}
                >
                  {isCompleted ? "✓" : index + 1}
                </div>
              </div>

              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className={`font-medium ${isActive ? "text-indigo-600" : "text-gray-900"}`}>
                    {phase.label}
                  </h3>
                  <span className="text-sm text-gray-500">
                    {phase.agents} agent{phase.agents > 1 ? "s" : ""}
                  </span>
                </div>
                {isActive && (
                  <p className="text-sm text-gray-600 mt-1">
                    Running now...
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
