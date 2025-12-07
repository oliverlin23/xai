"""
Agent implementations
"""
from app.agents.superforecaster.discovery import DiscoveryAgent
from app.agents.superforecaster.validation import (
    ValidatorAgent, 
    RaterAgent, 
    ConsensusAgent,
    RatingConsensusAgent  # Merged agent (recommended)
)
from app.agents.superforecaster.research import HistoricalResearchAgent, CurrentDataResearchAgent
from app.agents.superforecaster.synthesis import SynthesisAgent

__all__ = [
    "DiscoveryAgent",
    "ValidatorAgent",
    "RaterAgent",
    "ConsensusAgent",
    "RatingConsensusAgent",  # Merged agent (recommended)
    "HistoricalResearchAgent",
    "CurrentDataResearchAgent",
    "SynthesisAgent",
]
