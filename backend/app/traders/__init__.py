"""
Traders module - Contains prediction market trading agents

Available agents:
- NoiseTrader: Monitors X spheres of influence for prediction context
- UserAgent: Monitors specific X accounts for prediction context
- FundamentalAgent: (Coming soon) Fundamental analysis-based trading
"""

from app.traders.noise_agent import (
    NoiseTrader,
    NoiseAgent,  # Backwards compatibility alias
    NoiseTraderOutput,
    create_noise_trader,
)
from app.traders.user_agent import (
    UserAgent,
    UserAgentOutput,
    UserAccountFilter,
    USER_ACCOUNT_MAPPINGS,
    create_user_agent,
    get_user_agent_names,
)
from app.traders.semantic_filter import (
    SemanticFilter,
    SemanticFilterConfig,
    SemanticFilterOutput,
    FullSemanticFilterOutput,
    semantic_search,
)

__all__ = [
    # Noise Trader
    "NoiseTrader",
    "NoiseAgent",
    "NoiseTraderOutput",
    "create_noise_trader",
    # User Agent
    "UserAgent",
    "UserAgentOutput",
    "UserAccountFilter",
    "USER_ACCOUNT_MAPPINGS",
    "create_user_agent",
    "get_user_agent_names",
    # Semantic Filter
    "SemanticFilter",
    "SemanticFilterConfig",
    "SemanticFilterOutput",
    "FullSemanticFilterOutput",
    "semantic_search",
]
