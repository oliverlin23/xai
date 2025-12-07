"""
Phase 1: Discovery Agents (Agents 1-10)
Each agent discovers up to 5 factors independently with diverse perspectives
"""
from typing import Dict, Any, Optional
from app.agents.base import BaseAgent
from app.agents.superforecaster.prompts import get_discovery_prompt
from app.schemas import FactorDiscoveryOutput


class DiscoveryAgent(BaseAgent):
    """Discovery agent for Phase 1 with diverse perspectives"""
    
    def __init__(self, agent_number: int, session_id: Optional[str] = None):
        # Get perspective-specific prompt and temperature
        system_prompt, temperature = get_discovery_prompt(agent_number)
        
        super().__init__(
            agent_name=f"discovery_{agent_number}",
            phase="factor_discovery",
            system_prompt=system_prompt,
            output_schema=FactorDiscoveryOutput,
            session_id=session_id,
            temperature=temperature
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

