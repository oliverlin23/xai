"""
Phase 2: Validation Agents (Agents 11-13)
Sequential agents: Validator → Rater → Consensus Builder
"""
from typing import Dict, Any, Optional
from app.agents.base import BaseAgent
from app.agents.prompts import (
    VALIDATOR_AGENT_PROMPT,
    RATER_AGENT_PROMPT,
    CONSENSUS_AGENT_PROMPT
)
from app.schemas import (
    FactorValidationOutput,
    FactorRatingOutput,
    ConsensusOutput
)


class ValidatorAgent(BaseAgent):
    """Agent 11: Validates and deduplicates factors"""
    
    def __init__(self, session_id: Optional[str] = None):
        super().__init__(
            agent_name="validator",
            phase="validation",
            system_prompt=VALIDATOR_AGENT_PROMPT,
            output_schema=FactorValidationOutput,
            session_id=session_id
        )
    
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build user message with all discovered factors"""
        factors = input_data.get("factors", [])
        question_text = input_data.get("question_text", "")
        
        factors_text = "\n".join([
            f"- {f.get('name', 'Unknown')}: {f.get('description', '')} ({f.get('category', 'unknown')})"
            for f in factors
        ])
        
        return f"""Forecasting Question: {question_text}

Discovered Factors ({len(factors)} total):
{factors_text}

Review these factors, deduplicate similar ones, and validate their relevance. 
Return a clean list of unique, validated factors."""


class RaterAgent(BaseAgent):
    """Agent 12: Rates factor importance (1-10)"""
    
    def __init__(self, session_id: Optional[str] = None):
        super().__init__(
            agent_name="rater",
            phase="validation",
            system_prompt=RATER_AGENT_PROMPT,
            output_schema=FactorRatingOutput,
            session_id=session_id
        )
    
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build user message with validated factors"""
        factors = input_data.get("factors", [])
        question_text = input_data.get("question_text", "")
        
        factors_text = "\n".join([
            f"- {f.get('name', 'Unknown')}: {f.get('description', '')}"
            for f in factors
        ])
        
        return f"""Forecasting Question: {question_text}

Validated Factors ({len(factors)} total):
{factors_text}

Rate each factor's importance on a scale of 1-10. 
Consider: direct impact, historical precedence, current relevance, data availability."""


class ConsensusAgent(BaseAgent):
    """Agent 13: Selects top 5 factors for research"""
    
    def __init__(self, session_id: Optional[str] = None):
        super().__init__(
            agent_name="consensus",
            phase="validation",
            system_prompt=CONSENSUS_AGENT_PROMPT,
            output_schema=ConsensusOutput,
            session_id=session_id
        )
    
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build user message with rated factors"""
        factors = input_data.get("factors", [])
        question_text = input_data.get("question_text", "")
        
        # Sort by importance score if available (handle None values properly)
        # Separate factors with scores from those without, then sort and combine
        factors_with_scores = [f for f in factors if f.get("importance_score") is not None]
        factors_without_scores = [f for f in factors if f.get("importance_score") is None]
        sorted_factors = sorted(factors_with_scores, key=lambda f: f.get("importance_score", 0), reverse=True) + factors_without_scores
        
        factors_text = "\n".join([
            f"- {f.get('name', 'Unknown')} (Importance: {f.get('importance_score', 'N/A')}/10): {f.get('description', '')}"
            for f in sorted_factors
        ])
        
        return f"""Forecasting Question: {question_text}

Rated Factors ({len(factors)} total):
{factors_text}

Select the top 5 most important factors for deep research.
Consider: importance scores, category diversity, research feasibility.
Return exactly 5 factors."""

