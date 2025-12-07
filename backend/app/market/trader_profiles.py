"""
Utility functions for generating trader profiles and descriptions.
"""
from typing import Optional, Dict, Any
from app.market.models import TraderType, get_trader_type, FUNDAMENTAL_TRADERS, NOISE_TRADERS
from app.agents.prompts import FORECASTER_CLASSES

# Try to import sphere data, but handle gracefully if not available
try:
    from x_search.communities import get_sphere
except ImportError:
    get_sphere = None


def get_trader_description(trader_name: str, system_prompt: Optional[str] = None) -> str:
    """
    Generate a human-readable description for a trader.
    
    Args:
        trader_name: Name of the trader
        system_prompt: Optional system prompt (used to extract additional context)
        
    Returns:
        Description string
    """
    trader_type = get_trader_type(trader_name)
    
    if trader_type == TraderType.FUNDAMENTAL:
        # Use forecaster class descriptions
        if trader_name in FORECASTER_CLASSES:
            class_info = FORECASTER_CLASSES[trader_name]
            return f"{class_info['name']}. {class_info['description']}"
        else:
            # Fallback for fundamental traders
            name_map = {
                "conservative": "Conservative Institutional Trader",
                "momentum": "Aggressive Momentum Trader",
                "historical": "Historical Pattern Analyst",
                "balanced": "Balanced Synthesizer",
                "realtime": "Current Data Specialist",
            }
            return name_map.get(trader_name, f"Fundamental trader: {trader_name}")
    
    elif trader_type == TraderType.NOISE:
        # Use sphere descriptions
        if get_sphere:
            sphere = get_sphere(trader_name)
            if sphere:
                return f"Monitors the '{sphere.name}' sphere on X. {sphere.vibe} Typical participants: {sphere.followers}. Core beliefs: {sphere.core_beliefs}"
        
        # Fallback for noise traders
        name_map = {
            "eacc_sovereign": "Monitors e/acc & Sovereign Individual sphere - techno-optimist, libertarian traders",
            "america_first": "Monitors America First & Right Wing sphere - nationalist, populist perspectives",
            "blue_establishment": "Monitors Blue Establishment sphere - mainstream Democratic viewpoints",
            "progressive_left": "Monitors Progressive Left sphere - progressive, activist perspectives",
            "optimizer_idw": "Monitors Optimizer & IDW sphere - rationalist, intellectual discourse",
            "fintwit_market": "Monitors FinTwit & Market sphere - financial market sentiment",
            "builder_engineering": "Monitors Builder & Engineering sphere - technical, product-focused",
            "academic_research": "Monitors Academic & Research sphere - scholarly, evidence-based",
            "osint_intel": "Monitors OSINT & Intel sphere - open source intelligence, security-focused",
        }
        return name_map.get(trader_name, f"Noise trader monitoring: {trader_name}")
    
    elif trader_type == TraderType.USER:
        # User traders
        return f"User trader: {trader_name.capitalize()}"
    
    return f"Trader: {trader_name}"


def get_trader_display_name(trader_name: str) -> str:
    """
    Get a human-readable display name for a trader.
    
    Args:
        trader_name: Name of the trader
        
    Returns:
        Display name string
    """
    trader_type = get_trader_type(trader_name)
    
    if trader_type == TraderType.FUNDAMENTAL:
        if trader_name in FORECASTER_CLASSES:
            return FORECASTER_CLASSES[trader_name]["name"]
        return trader_name.replace("_", " ").title()
    
    elif trader_type == TraderType.NOISE:
        if get_sphere:
            sphere = get_sphere(trader_name)
            if sphere:
                return sphere.name
        return trader_name.replace("_", " ").title()
    
    elif trader_type == TraderType.USER:
        return trader_name.capitalize()
    
    return trader_name.replace("_", " ").title()


def get_trader_role(trader_name: str) -> str:
    """
    Get a role/category for a trader (for UI display).
    
    Args:
        trader_name: Name of the trader
        
    Returns:
        Role string
    """
    trader_type = get_trader_type(trader_name)
    
    if trader_type == TraderType.FUNDAMENTAL:
        return "Fundamental Analyst"
    elif trader_type == TraderType.NOISE:
        return "Noise Trader"
    elif trader_type == TraderType.USER:
        return "User Trader"
    
    return "Trader"

