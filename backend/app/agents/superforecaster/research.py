"""
Phase 3: Research Agents (Agents 14-23)
10 agents: 5 historical + 5 current data researchers
"""
from typing import Dict, Any, Optional
from app.agents.base import BaseAgent
from app.agents.superforecaster.prompts import (
    HISTORICAL_RESEARCH_PROMPT,
    CURRENT_DATA_RESEARCH_PROMPT
)
from app.schemas import (
    HistoricalResearchOutput,
    CurrentDataOutput
)


class HistoricalResearchAgent(BaseAgent):
    """Agents 14-18: Historical pattern analysts"""
    
    def __init__(self, agent_number: int, session_id: Optional[str] = None):
        super().__init__(
            agent_name=f"historical_{agent_number}",
            phase="research",
            system_prompt=HISTORICAL_RESEARCH_PROMPT,
            output_schema=HistoricalResearchOutput,
            session_id=session_id
        )
        self.agent_number = agent_number
    
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build user message with factor to research, instructing web search"""
        factor = input_data.get("factor", {})
        question_text = input_data.get("question_text", "")
        
        factor_name = factor.get("name", "Unknown")
        factor_desc = factor.get("description", "")
        factor_category = factor.get("category", "")
        
        return f"""Forecasting Question: {question_text}

Factor to Research:
Name: {factor_name}
Description: {factor_desc}
Category: {factor_category}

First, search the web for historical data, past occurrences, and long-term trends related to this factor and the forecasting question. Use the search results to inform your analysis.

Then, research historical precedents, patterns, and analogous situations for this factor.
Analyze past occurrences and long-term trends.
Provide detailed historical context and your confidence level (0-1).
Include sources from your web search when relevant."""


class CurrentDataResearchAgent(BaseAgent):
    """Agents 19-23: Current data researchers"""
    
    def __init__(self, agent_number: int, session_id: Optional[str] = None):
        super().__init__(
            agent_name=f"current_{agent_number}",
            phase="research",
            system_prompt=CURRENT_DATA_RESEARCH_PROMPT,
            output_schema=CurrentDataOutput,
            session_id=session_id
        )
        self.agent_number = agent_number
    
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build user message with factor to research, instructing web search"""
        factor = input_data.get("factor", {})
        question_text = input_data.get("question_text", "")
        
        factor_name = factor.get("name", "Unknown")
        factor_desc = factor.get("description", "")
        factor_category = factor.get("category", "")
        
        return f"""Forecasting Question: {question_text}

Factor to Research:
Name: {factor_name}
Description: {factor_desc}
Category: {factor_category}

First, search the web for the most recent information, news, statistics, and developments related to this factor and the forecasting question. Use the search results as your primary source of current information.

Then, research current data, recent developments, and emerging trends for this factor.
Analyze latest statistics, news, and current events.
Provide up-to-date findings and your confidence level (0-1).
Include sources from your web search when relevant."""

