"use client"

import { useState } from "react"

interface AgentCounts {
  phase_1_discovery?: number
  phase_2_validation?: number
  phase_3_research?: number  // Backward compatible - splits 50/50 if phase_3_historical/current not provided
  phase_3_historical?: number  // Historical research agents
  phase_3_current?: number  // Current research agents
  phase_4_synthesis?: number
}

interface QuestionInputProps {
  onSubmit: (questionText: string, questionType: string, agentCounts?: AgentCounts, forecasterClass?: string) => void
  isSubmitting: boolean
}

export function QuestionInput({ onSubmit, isSubmitting }: QuestionInputProps) {
  const [questionText, setQuestionText] = useState("")
  const [questionType, setQuestionType] = useState("binary")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [forecasterClass, setForecasterClass] = useState("balanced")
  const [agentCounts, setAgentCounts] = useState<AgentCounts>({
    phase_1_discovery: 10,
    phase_2_validation: 2,
    phase_3_research: 10,
    phase_4_synthesis: 1,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (questionText.trim()) {
      onSubmit(questionText, questionType, agentCounts, forecasterClass)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 text-[#0f172a]">
      <div>
        <label htmlFor="question" className="block text-sm font-medium text-slate-700 mb-2">
          Forecasting Question
        </label>
        <textarea
          id="question"
          value={questionText}
          onChange={(e) => setQuestionText(e.target.value)}
          placeholder="e.g., Will Bitcoin reach $150,000 by December 31, 2025?"
          className="w-full px-4 py-3 rounded-lg bg-white border border-[#d9dde7] text-[#0f172a] placeholder:text-slate-500 focus:ring-2 focus:ring-[#2d7dd2]/70 focus:border-[#2d7dd2]/70 shadow-[0_6px_20px_rgba(0,0,0,0.08)] resize-none transition"
          rows={4}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="type" className="block text-sm font-medium text-slate-700 mb-2">
            Question Type
          </label>
          <select
            id="type"
            value={questionType}
            onChange={(e) => setQuestionType(e.target.value)}
            className="w-full px-4 py-3 rounded-lg bg-white border border-[#d9dde7] text-[#0f172a] focus:ring-2 focus:ring-[#2d7dd2]/70 focus:border-[#2d7dd2]/70 transition shadow-[0_6px_20px_rgba(0,0,0,0.06)]"
            disabled={isSubmitting}
          >
            <option value="binary">Binary (Yes/No)</option>
            <option value="numeric">Numeric Range</option>
            <option value="categorical">Categorical</option>
          </select>
        </div>
        
        <div>
          <label htmlFor="forecasterClass" className="block text-sm font-medium text-slate-700 mb-2">
            Forecaster Class
          </label>
          <select
            id="forecasterClass"
            value={forecasterClass}
            onChange={(e) => setForecasterClass(e.target.value)}
            className="w-full px-4 py-3 rounded-lg bg-white border border-[#d9dde7] text-[#0f172a] focus:ring-2 focus:ring-[#2d7dd2]/70 focus:border-[#2d7dd2]/70 transition shadow-[0_6px_20px_rgba(0,0,0,0.06)]"
            disabled={isSubmitting}
          >
            <option value="balanced">Balanced (Default)</option>
            <option value="conservative">Conservative</option>
            <option value="momentum">Momentum</option>
            <option value="historical">Historical</option>
            <option value="realtime">Real-time</option>
          </select>
        </div>
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-[#2d7dd2] hover:text-[#1f5fa0] font-medium"
          disabled={isSubmitting}
        >
          {showAdvanced ? "▼" : "▶"} Advanced: Agent Configuration
        </button>
        
        {showAdvanced && (
          <div className="mt-4 p-4 bg-white/90 border border-[#d9dde7] rounded-lg space-y-4 shadow-[0_10px_30px_rgba(0,0,0,0.08)]">
            {forecasterClass !== "balanced" ? (
              <div className="mb-3 p-3 bg-[#eef2f7] border border-[#c6d3e6] rounded-md">
                <p className="text-sm text-[#1f5fa0] font-medium mb-1">
                  ⓘ Agent Configuration Disabled
                </p>
                <p className="text-xs text-slate-700">
                  The "{forecasterClass}" forecaster class uses its own optimized agent counts. 
                  Switch to "Balanced" to customize agent counts.
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-700 mb-3">
                Configure how many agents run in each phase (default: 10, 2, 10, 1 = 23 total)
              </p>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="phase1" className="block text-xs font-medium text-slate-700 mb-1">
                  Phase 1: Discovery
                </label>
                <input
                  id="phase1"
                  type="number"
                  min="1"
                  max="20"
                  value={agentCounts.phase_1_discovery}
                  onChange={(e) => setAgentCounts({...agentCounts, phase_1_discovery: parseInt(e.target.value) || 10})}
                  className="w-full px-3 py-2 rounded-md text-sm bg-white border border-[#d9dde7] text-[#0f172a] focus:ring-2 focus:ring-[#2d7dd2]/70 focus:border-[#2d7dd2]/70 transition shadow-[0_4px_12px_rgba(0,0,0,0.06)]"
                  disabled={isSubmitting || forecasterClass !== "balanced"}
                />
              </div>
              
              <div>
                <label htmlFor="phase2" className="block text-xs font-medium text-slate-700 mb-1">
                  Phase 2: Validation
                </label>
                <input
                  id="phase2"
                  type="number"
                  min="2"
                  max="2"
                  value={agentCounts.phase_2_validation}
                  onChange={(e) => setAgentCounts({...agentCounts, phase_2_validation: 2})}
                  className="w-full px-3 py-2 rounded-md text-sm bg-[#eef2f7] border border-[#d9dde7] text-slate-600"
                  disabled={true}
                  title="Always 2 agents (validator, rating_consensus merged)"
                />
              </div>
              
              <div>
                <label htmlFor="phase3" className="block text-xs font-medium text-slate-700 mb-1">
                  Phase 3: Research
                </label>
                <input
                  id="phase3"
                  type="number"
                  min="2"
                  max="20"
                  value={agentCounts.phase_3_research}
                  onChange={(e) => setAgentCounts({...agentCounts, phase_3_research: parseInt(e.target.value) || 10})}
                  className="w-full px-3 py-2 rounded-md text-sm bg-white border border-[#d9dde7] text-[#0f172a] focus:ring-2 focus:ring-[#2d7dd2]/70 focus:border-[#2d7dd2]/70 transition shadow-[0_4px_12px_rgba(0,0,0,0.06)]"
                  disabled={isSubmitting || forecasterClass !== "balanced"}
                />
                <p className="text-xs text-slate-600 mt-1">Split: half historical, half current</p>
              </div>
              
              <div>
                <label htmlFor="phase4" className="block text-xs font-medium text-slate-700 mb-1">
                  Phase 4: Synthesis
                </label>
                <input
                  id="phase4"
                  type="number"
                  min="1"
                  max="1"
                  value={agentCounts.phase_4_synthesis}
                  onChange={(e) => setAgentCounts({...agentCounts, phase_4_synthesis: 1})}
                  className="w-full px-3 py-2 rounded-md text-sm bg-[#eef2f7] border border-[#d9dde7] text-slate-600"
                  disabled={true}
                  title="Always 1 agent"
                />
              </div>
            </div>
            
            {forecasterClass === "balanced" && (
              <div className="pt-2 border-t border-gray-200">
                <p className="text-xs text-slate-600">
                  Total agents: {(agentCounts.phase_1_discovery || 0) + (agentCounts.phase_2_validation || 0) + (agentCounts.phase_3_research || 0) + (agentCounts.phase_4_synthesis || 0)}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !questionText.trim()}
        className="w-full bg-[#2d7dd2] text-white py-3 px-6 rounded-lg font-semibold hover:bg-[#2568ad] disabled:bg-slate-400 disabled:text-white/80 disabled:cursor-not-allowed transition-colors shadow-[0_12px_30px_rgba(0,0,0,0.18)]"
      >
        {isSubmitting ? "Creating Forecast..." : "Start Forecasting"}
      </button>
    </form>
  )
}
