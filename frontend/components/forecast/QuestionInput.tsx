"use client"

import { useState } from "react"

interface AgentCounts {
  phase_1_discovery: number
  phase_2_validation: number
  phase_3_research: number
  phase_4_synthesis: number
}

interface QuestionInputProps {
  onSubmit: (questionText: string, questionType: string, agentCounts?: AgentCounts) => void
  isSubmitting: boolean
}

export function QuestionInput({ onSubmit, isSubmitting }: QuestionInputProps) {
  const [questionText, setQuestionText] = useState("")
  const [questionType, setQuestionType] = useState("binary")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [agentCounts, setAgentCounts] = useState<AgentCounts>({
    phase_1_discovery: 10,
    phase_2_validation: 3,
    phase_3_research: 10,
    phase_4_synthesis: 1,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (questionText.trim()) {
      onSubmit(questionText, questionType, agentCounts)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
          Forecasting Question
        </label>
        <textarea
          id="question"
          value={questionText}
          onChange={(e) => setQuestionText(e.target.value)}
          placeholder="e.g., Will Bitcoin reach $150,000 by December 31, 2025?"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          rows={4}
          required
          disabled={isSubmitting}
        />
      </div>

      <div>
        <label htmlFor="type" className="block text-sm font-medium text-gray-700 mb-2">
          Question Type
        </label>
        <select
          id="type"
          value={questionType}
          onChange={(e) => setQuestionType(e.target.value)}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          disabled={isSubmitting}
        >
          <option value="binary">Binary (Yes/No)</option>
          <option value="numeric">Numeric Range</option>
          <option value="categorical">Categorical</option>
        </select>
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          disabled={isSubmitting}
        >
          {showAdvanced ? "▼" : "▶"} Advanced: Agent Configuration
        </button>
        
        {showAdvanced && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
            <p className="text-sm text-gray-600 mb-3">
              Configure how many agents run in each phase (default: 10, 3, 10, 1 = 24 total)
            </p>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="phase1" className="block text-xs font-medium text-gray-700 mb-1">
                  Phase 1: Discovery
                </label>
                <input
                  id="phase1"
                  type="number"
                  min="1"
                  max="20"
                  value={agentCounts.phase_1_discovery}
                  onChange={(e) => setAgentCounts({...agentCounts, phase_1_discovery: parseInt(e.target.value) || 10})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  disabled={isSubmitting}
                />
              </div>
              
              <div>
                <label htmlFor="phase2" className="block text-xs font-medium text-gray-700 mb-1">
                  Phase 2: Validation
                </label>
                <input
                  id="phase2"
                  type="number"
                  min="3"
                  max="3"
                  value={agentCounts.phase_2_validation}
                  onChange={(e) => setAgentCounts({...agentCounts, phase_2_validation: 3})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-gray-100"
                  disabled={true}
                  title="Always 3 agents (validator, rater, consensus)"
                />
              </div>
              
              <div>
                <label htmlFor="phase3" className="block text-xs font-medium text-gray-700 mb-1">
                  Phase 3: Research
                </label>
                <input
                  id="phase3"
                  type="number"
                  min="2"
                  max="20"
                  value={agentCounts.phase_3_research}
                  onChange={(e) => setAgentCounts({...agentCounts, phase_3_research: parseInt(e.target.value) || 10})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  disabled={isSubmitting}
                />
                <p className="text-xs text-gray-500 mt-1">Split: half historical, half current</p>
              </div>
              
              <div>
                <label htmlFor="phase4" className="block text-xs font-medium text-gray-700 mb-1">
                  Phase 4: Synthesis
                </label>
                <input
                  id="phase4"
                  type="number"
                  min="1"
                  max="1"
                  value={agentCounts.phase_4_synthesis}
                  onChange={(e) => setAgentCounts({...agentCounts, phase_4_synthesis: 1})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-gray-100"
                  disabled={true}
                  title="Always 1 agent"
                />
              </div>
            </div>
            
            <div className="pt-2 border-t border-gray-200">
              <p className="text-xs text-gray-600">
                Total agents: {agentCounts.phase_1_discovery + agentCounts.phase_2_validation + agentCounts.phase_3_research + agentCounts.phase_4_synthesis}
              </p>
            </div>
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !questionText.trim()}
        className="w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        {isSubmitting ? "Creating Forecast..." : "Start Forecasting"}
      </button>
    </form>
  )
}
