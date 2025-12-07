"""
Phase 1: Discovery Agents (Agents 1-10)
Each agent discovers up to 5 factors independently
"""
from typing import Dict, Any, Optional
from app.agents.base import BaseAgent
from app.agents.prompts import DISCOVERY_AGENT_PROMPT
from app.schemas import FactorDiscoveryOutput


class DiscoveryAgent(BaseAgent):
    """Discovery agent for Phase 1"""
    
    def __init__(self, agent_number: int, session_id: Optional[str] = None):
        super().__init__(
            agent_name=f"discovery_{agent_number}",
            phase="factor_discovery",
            system_prompt=DISCOVERY_AGENT_PROMPT,
            output_schema=FactorDiscoveryOutput,
            session_id=session_id
        )
        self.agent_number = agent_number
    
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build user message from input data with web search instruction"""
        question_text = input_data.get("question_text", "")
        question_type = input_data.get("question_type", "binary")
        
        return f"""Forecasting Question: {question_text}
Question Type: {question_type}

First, search the web for current information, trends, and recent developments related to this forecasting question. Use the search results to inform your factor discovery.

Then, discover up to 5 relevant factors that could influence this outcome. 
Consider diverse perspectives and categories. Be creative and thorough.
Ensure your factors reflect current information and trends from your web search."""

