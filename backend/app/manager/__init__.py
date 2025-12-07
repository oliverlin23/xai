"""
Manager module for post-forecast market simulation.

This module orchestrates prediction markets after the Superforecaster completes:
- Creates markets based on forecast questions
- Provides liquidity via Avellaneda-Stoikov Market Maker
- Spawns Noise Traders that react to live X/Twitter sentiment
"""

from .market_maker import AvellanedaStoikovMM, MMConfig
from .manager import SimulationManager

__all__ = ["AvellanedaStoikovMM", "MMConfig", "SimulationManager"]

