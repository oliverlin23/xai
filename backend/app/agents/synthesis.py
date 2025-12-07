"""
Phase 4: Synthesis Agent (Agent 24)
Combines all research into final prediction
"""
from typing import Dict, Any, Optional
from app.agents.base import BaseAgent
from app.agents.prompts import SYNTHESIS_AGENT_PROMPT
from app.schemas import PredictionOutput


class SynthesisAgent(BaseAgent):
    """Agent 24: Prediction synthesizer"""
    
    def __init__(self, session_id: Optional[str] = None):
        super().__init__(
            agent_name="synthesizer",
            phase="synthesis",
            system_prompt=SYNTHESIS_AGENT_PROMPT,
            output_schema=PredictionOutput,
            session_id=session_id
        )
    
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build user message with all research data"""
        question_text = input_data.get("question_text", "")
        question_type = input_data.get("question_type", "binary")
        factors = input_data.get("factors", [])
        research_data = input_data.get("research", {})
        
        # Format factors with research
        factors_text = ""
        for factor in factors:
            name = factor.get("name", "Unknown")
            importance = factor.get("importance_score", "N/A")
            research = factor.get("research_summary", "No research available")
            
            factors_text += f"""
Factor: {name} (Importance: {importance}/10)
Research Summary:
{research}
---
"""
        
        return f"""Forecasting Question: {question_text}
Question Type: {question_type}

Research Summary for Top Factors:
{factors_text}

Synthesize all this research into a coherent prediction.
Apply superforecasting principles:
- Base rates and outside view
- Break down complex questions  
- Consider multiple perspectives
- Express uncertainty calibrated to evidence

Provide:
1. A clear prediction statement
2. Confidence score (0-1)
3. Detailed reasoning
4. List of key factors that influenced your prediction"""

