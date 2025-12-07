"""
Traders module - Contains prediction market trading agents

Available agents:
- NoiseTrader: Monitors X spheres of influence for prediction context
- UserAgent: Monitors specific X accounts for prediction context
- FundamentalTrader: Trades on market data and prior reasoning only (no X API)
"""

from app.agents.traders.noise_agent import (
    NoiseTrader,
    NoiseAgent,  # Backwards compatibility alias
    NoiseTraderOutput,
    create_noise_trader,
)
from app.agents.traders.user_agent import (
    UserAgent,
    UserAgentOutput,
    UserAccountFilter,
    USER_ACCOUNT_MAPPINGS,
    create_user_agent,
    get_user_agent_names,
)
from app.agents.traders.fundamental_agent import (
    FundamentalTrader,
    FundamentalAgent,  # Backwards compatibility alias
    FundamentalTraderOutput,
    FUNDAMENTAL_TRADER_TYPES,
    get_fundamental_trader_names,
)
from app.agents.traders.semantic_filter import (
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
    # Fundamental Trader
    "FundamentalTrader",
    "FundamentalAgent",
    "FundamentalTraderOutput",
    "FUNDAMENTAL_TRADER_TYPES",
    "get_fundamental_trader_names",
    # Semantic Filter
    "SemanticFilter",
    "SemanticFilterConfig",
    "SemanticFilterOutput",
    "FullSemanticFilterOutput",
    "semantic_search",
]
