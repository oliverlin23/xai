"""
Avellaneda-Stoikov Market Maker for Prediction Markets.

Adapts the classic high-frequency trading model to prediction markets (0-100 cents).

=== INPUT FROM SUPERFORECASTER ===
We receive exactly TWO values from the Superforecaster:
1. prediction_probability (p): The forecasted probability of YES (0.0 to 1.0)
2. confidence (c): How certain the forecaster is in that probability (0.0 to 1.0)

=== PARAMETER DERIVATION ===
From these two values, we derive all Avellaneda-Stoikov parameters:

1. Mid Price (s):
   s = p * 100 cents
   Example: p=0.65 -> s=65 cents (market thinks 65% chance of YES)

2. Volatility (σ):
   We interpret the forecast as a belief distribution N(μ=p, σ²).
   High confidence → narrow distribution → low σ
   Low confidence → wide distribution → high σ
   
   Formula: σ = σ_base * (1 - c)
   
   Example: c=0.8 (high confidence) → σ = 2.0 * 0.2 = 0.4 (tight quotes)
   Example: c=0.3 (low confidence) → σ = 2.0 * 0.7 = 1.4 (wide quotes)

Reference: Avellaneda, M. and Stoikov, S., "High-frequency trading in a limit order book", 2008.
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class MMConfig:
    """
    Configuration for Avellaneda-Stoikov Market Maker.
    
    These are algorithm parameters, NOT derived from the forecast.
    They control how the MM behaves (risk tolerance, quote sizes, etc.)
    
    Calibrated for prediction markets (0-100 cent price range).
    """
    # gamma: How much the MM dislikes holding inventory
    # Lower = more gradual inventory skew (quotes shift slowly with position)
    # Calibrated so inv=±30 shifts quotes by ~15-20 cents
    risk_aversion: float = 0.003
    
    # k: Order arrival rate parameter (affects base spread)
    # Higher = expects more order flow = tighter spreads
    liquidity_param: float = 1.2
    
    # T: Time horizon for the simulation (in seconds)
    terminal_time: float = 60.0
    
    # σ_base: Maximum volatility when confidence = 0
    # The actual σ = σ_base * (1 - confidence)
    # Controls how spread widens with uncertainty
    volatility_base: float = 3.5
    
    # Minimum spread in cents (realistic for prediction markets)
    min_spread: int = 2
    
    # Maximum inventory before MM becomes very aggressive
    max_inventory: int = 100


class AvellanedaStoikovMM:
    """
    Market Maker that provides liquidity based on Superforecaster beliefs.
    
    The MM quotes bid/ask around a "reservation price" that adjusts based on:
    - The forecast probability (fair value)
    - Current inventory (risk management)
    - Time remaining (urgency to flatten)
    - Forecast confidence (quote width)
    """
    
    def __init__(
        self,
        prediction_probability: float,
        confidence: float,
        config: Optional[MMConfig] = None
    ):
        """
        Initialize Market Maker with Superforecaster output.
        
        Args:
            prediction_probability: From Superforecaster (0.0 to 1.0)
                                    The forecasted probability of YES.
            confidence: From Superforecaster (0.0 to 1.0)
                        How certain the forecast is in that probability.
            config: Algorithm parameters (optional, uses defaults)
        """
        self.config = config or MMConfig()
        
        # === DERIVED FROM SUPERFORECASTER ===
        
        # Mid Price: Convert probability to cents (0-100)
        # This is the MM's belief about the "true" price
        self.mid_price = prediction_probability * 100.0
        
        # Volatility: Derived from confidence
        # Interpretation: The forecast belief is N(μ=p, σ²)
        # High confidence -> small σ -> tight quotes
        # Low confidence -> large σ -> wide quotes
        self.sigma = self.config.volatility_base * (1.0 - confidence)
        
        # === MM STATE ===
        self.inventory = 0  # q: net YES contracts held (positive=long, negative=short)
        self.cash = 0.0     # Running PnL tracking
        
        # Store original inputs for reference
        self._prediction_probability = prediction_probability
        self._confidence = confidence
        
    def get_quotes(self, current_time: float) -> Tuple[Optional[int], Optional[int]]:
        """
        Calculate optimal bid and ask prices using Avellaneda-Stoikov formula.
        
        The key insight: The MM adjusts its quotes based on inventory.
        - If long (positive inventory): Lower bid to discourage buying, lower ask to encourage selling
        - If short (negative inventory): Raise bid to encourage buying, raise ask to discourage selling
        
        Args:
            current_time: Current simulation time (0 to T)
            
        Returns:
            (bid_price, ask_price) in integer cents (1-99).
            Returns (None, None) if market closed or invalid.
        """
        T = self.config.terminal_time
        t = min(current_time, T)
        
        # Remaining time
        dt = T - t
        if dt <= 0:
            return None, None
            
        # 1. Reservation Price (r)
        # r(s, t) = s - q * γ * σ² * (T - t)
        # This is the MM's "indifference price" - adjusted for inventory risk
        inventory_adjustment = self.inventory * self.config.risk_aversion * (self.sigma ** 2) * dt
        reservation_price = self.mid_price - inventory_adjustment
        
        # 2. Optimal Spread (δ)
        # δ = γ * σ² * (T-t) + (2/γ) * ln(1 + γ/k)
        # First term: volatility/time risk
        # Second term: compensation for adverse selection
        spread_time_risk = self.config.risk_aversion * (self.sigma ** 2) * dt
        spread_adverse_selection = (2.0 / self.config.risk_aversion) * math.log(
            1.0 + self.config.risk_aversion / self.config.liquidity_param
        )
        optimal_spread = spread_time_risk + spread_adverse_selection
        
        # Enforce minimum spread
        optimal_spread = max(optimal_spread, self.config.min_spread)
        
        # 3. Final Quotes
        bid_price = reservation_price - (optimal_spread / 2.0)
        ask_price = reservation_price + (optimal_spread / 2.0)
        
        # Round to integer cents
        bid = int(round(bid_price))
        ask = int(round(ask_price))
        
        # Clamp to valid prediction market range (1-99)
        bid = max(1, min(99, bid))
        ask = max(1, min(99, ask))
        
        # Prevent crossed book from rounding
        if bid >= ask:
            if bid > 1:
                bid -= 1
            if ask < 99:
                ask += 1
            
        return bid, ask

    def on_fill(self, quantity: int, side: str, price: int):
        """
        Update state after MM order is filled.
        
        Args:
            quantity: Number of contracts filled
            side: "buy" (MM bought YES) or "sell" (MM sold YES)
            price: Execution price in cents
        """
        if side == "buy":
            self.inventory += quantity
            self.cash -= quantity * price
        else:  # "sell"
            self.inventory -= quantity
            self.cash += quantity * price
            
    def update_belief(self, market_price: float, alpha: float = 0.1):
        """
        Optionally update mid_price based on market moves.
        
        This allows the MM to slowly adapt if the market disagrees with the forecast.
        Set alpha=0 to keep the original Superforecaster belief fixed.
        
        Args:
            market_price: Current market mid price (0-100)
            alpha: Learning rate (0 = no update, 1 = fully adopt market price)
        """
        self.mid_price = (1 - alpha) * self.mid_price + alpha * market_price
        
    def get_state(self) -> dict:
        """Return current MM state for logging/debugging."""
        return {
            "mid_price": self.mid_price,
            "sigma": self.sigma,
            "inventory": self.inventory,
            "cash": self.cash,
            "original_probability": self._prediction_probability,
            "original_confidence": self._confidence,
        }
