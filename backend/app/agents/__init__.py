"""
Agent implementations
"""
from app.agents.discovery import DiscoveryAgent
from app.agents.validation import (
    ValidatorAgent, 
    RaterAgent, 
    ConsensusAgent,
    RatingConsensusAgent  # Merged agent (recommended)
)
from app.agents.research import HistoricalResearchAgent, CurrentDataResearchAgent
from app.agents.synthesis import SynthesisAgent

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
