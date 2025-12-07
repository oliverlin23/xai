"""
Simulation Manager for Prediction Markets.

=== SUPERFORECASTER OUTPUT ===
The Superforecaster provides exactly these fields (see app/schemas.py PredictionOutput):
- prediction: str                 # "Yes" or "No"
- prediction_probability: float   # 0.0-1.0: The probability of YES
- confidence: float               # 0.0-1.0: How confident in that probability
- reasoning: str                  # Explanation
- key_factors: List[str]          # Important factors

This Manager uses ONLY prediction_probability and confidence to initialize the market.

=== WORKFLOW ===
1. Receives prediction_result from completed Superforecaster session
2. Creates a prediction market for the question
3. Initializes Market Maker with (prediction_probability, confidence)
4. Spawns Noise Traders that analyze live X/Twitter sentiment
5. Runs simulation loop until duration expires
"""

import asyncio
import random
import time
from typing import Dict, Any, List, Optional

from app.market.models import Market, Order, OrderSide, OrderStatus
from app.market.orderbook import OrderBook
from app.noise_traders.noise_agent import NoiseTrader
from app.manager.market_maker import AvellanedaStoikovMM, MMConfig
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SimulationManager:
    """
    Orchestrates a prediction market simulation after Superforecaster completes.
    
    The Manager is deterministic in structure but uses live data via Noise Traders.
    """
    
    def __init__(
        self,
        session_id: str,
        question: str,
        prediction_result: Dict[str, Any],
        duration_seconds: int = 60,
        time_step: float = 1.0,
        trader_communities: Optional[List[str]] = None
    ):
        """
        Initialize simulation manager.
        
        Args:
            session_id: The Superforecaster session ID
            question: The forecast question (becomes market question)
            prediction_result: Output from Superforecaster containing:
                - prediction_probability (float 0-1): Probability of YES
                - confidence (float 0-1): Confidence in that probability
            duration_seconds: How long to run simulation
            time_step: Seconds between simulation steps
            trader_communities: Which X communities to spawn traders for
        """
        self.session_id = session_id
        self.question = question
        self.duration = duration_seconds
        self.time_step = time_step
        
        # === EXTRACT FROM SUPERFORECASTER ===
        # These are the ONLY two values we use from the forecast
        self.prediction_probability = prediction_result.get("prediction_probability", 0.5)
        self.confidence = prediction_result.get("confidence", 0.5)
        
        logger.info(f"[MANAGER] Initializing with Superforecaster output:")
        logger.info(f"[MANAGER]   prediction_probability = {self.prediction_probability}")
        logger.info(f"[MANAGER]   confidence = {self.confidence}")
        
        # === INITIALIZE MARKET ===
        self.market = Market(
            question=question,
            session_id=session_id,
            description=f"Simulation market for session {session_id}"
        )
        self.orderbook = OrderBook(self.market)
        
        # === INITIALIZE MARKET MAKER ===
        # Pass the two Superforecaster values directly
        self.mm = AvellanedaStoikovMM(
            prediction_probability=self.prediction_probability,
            confidence=self.confidence,
            config=MMConfig(terminal_time=float(duration_seconds))
        )
        self.mm_agent_id = "mm_avellaneda_001"
        
        logger.info(f"[MANAGER] Market Maker initialized:")
        logger.info(f"[MANAGER]   mid_price = {self.mm.mid_price:.2f} cents")
        logger.info(f"[MANAGER]   sigma = {self.mm.sigma:.4f}")
        
        # === INITIALIZE TRADERS ===
        self.traders: List[NoiseTrader] = []
        # Valid communities: tech_vc, maga_right, progressive_left, liberal_establishment,
        # conservative_establishment, crypto_web3, ai_ml, podcast_media
        self.trader_communities = trader_communities or ["crypto_web3", "tech_vc", "ai_ml", "podcast_media"]
        
    async def setup_traders(self):
        """Initialize noise traders for each community."""
        for community in self.trader_communities:
            try:
                trader = NoiseTrader(
                    community=community,
                    agent_name=f"trader_{community}",
                    enable_tools=True  # Enable live X search
                )
                self.traders.append(trader)
                logger.info(f"[MANAGER] Initialized trader for '{community}' community")
            except Exception as e:
                logger.error(f"[MANAGER] Failed to init trader {community}: {e}")

    async def run(self) -> Dict[str, Any]:
        """
        Run the market simulation.
        
        Returns:
            Dict containing simulation results:
            - market_id: Market identifier
            - initial_price: Starting price from forecast
            - final_price: Ending market price
            - total_volume: Total contracts traded
            - price_history: List of (time, price, volume) snapshots
            - mm_state: Final market maker state
        """
        logger.info(f"[MANAGER] Starting simulation for: '{self.question}'")
        logger.info(f"[MANAGER] Duration: {self.duration}s, Step: {self.time_step}s")
        
        await self.setup_traders()
        
        start_time = time.time()
        current_sim_time = 0.0
        
        price_history = []
        initial_price = self.prediction_probability * 100  # In cents
        
        while current_sim_time < self.duration:
            # 1. Market Maker updates quotes
            await self._run_mm_step(current_sim_time)
            
            # 2. Noise Traders act periodically (not every tick)
            if int(current_sim_time) % 5 == 0 and current_sim_time > 0:
                await self._run_traders_step()
            
            # 3. Record market state
            current_price = self.market.last_price or initial_price
            price_history.append({
                "time": current_sim_time,
                "price": current_price,
                "volume": self.market.volume
            })
                
            # Advance simulation time
            current_sim_time += self.time_step
            await asyncio.sleep(self.time_step)
            
        logger.info(f"[MANAGER] Simulation completed after {time.time() - start_time:.1f}s")
        
        return {
            "market_id": self.market.id,
            "session_id": self.session_id,
            "initial_price": initial_price,
            "final_price": self.market.last_price,
            "total_volume": self.market.volume,
            "price_history": price_history,
            "mm_state": self.mm.get_state(),
        }

    async def _run_mm_step(self, current_time: float):
        """Execute Market Maker quoting logic."""
        # Get optimal quotes from A-S model
        bid, ask = self.mm.get_quotes(current_time)
        
        if bid is None or ask is None:
            return

        # Cancel existing MM orders (simple cancel-replace strategy)
        active_orders = self.orderbook.get_agent_orders(self.mm_agent_id)
        for order in active_orders:
            try:
                self.orderbook.cancel_order(order.id, self.mm_agent_id)
            except Exception:
                pass
                
        # Place bid (Buy YES at bid price)
        bid_order = Order(
            agent_id=self.mm_agent_id,
            market_id=self.market.id,
            side=OrderSide.YES,
            price=bid,
            quantity=10
        )
        _, bid_trades = self.orderbook.place_order(bid_order)
        self._process_mm_trades(bid_trades)
        
        # Place ask (Sell YES at ask price)
        # In our YES/NO model: Selling YES at X = Buying NO at (100-X)
        no_price = 100 - ask
        ask_order = Order(
            agent_id=self.mm_agent_id,
            market_id=self.market.id,
            side=OrderSide.NO,
            price=no_price,
            quantity=10
        )
        _, ask_trades = self.orderbook.place_order(ask_order)
        self._process_mm_trades(ask_trades)

    def _process_mm_trades(self, trades: List[Any]):
        """Update MM inventory after trades."""
        for trade in trades:
            if trade.buyer_agent_id == self.mm_agent_id:
                # MM bought YES
                self.mm.on_fill(trade.quantity, "buy", trade.price)
            elif trade.seller_agent_id == self.mm_agent_id:
                # MM sold YES (was on NO side that matched)
                self.mm.on_fill(trade.quantity, "sell", trade.price)

    async def _run_traders_step(self):
        """Execute a Noise Trader's analysis and trading."""
        if not self.traders:
            return
            
        # Pick one trader randomly to act
        trader = random.choice(self.traders)
        
        # Build market context for the trader
        book_snapshot = self.orderbook.get_book_snapshot()
        market_context = {
            "market_topic": self.question,
            "order_book": book_snapshot,
            "recent_trades": [
                {"price": t.price, "quantity": t.quantity} 
                for t in self.orderbook.trades[-5:]
            ]
        }
        
        try:
            logger.info(f"[MANAGER] Trader '{trader.agent_name}' analyzing market...")
            prediction = await trader.execute(market_context)
            
            # Trader's prediction is 0-100 probability
            trader_prob = prediction.get("prediction", 50)
            current_mid = self.market.last_price or (self.prediction_probability * 100)
            
            # Only trade if there's meaningful edge (5 cent threshold)
            edge_threshold = 5
            qty = 5
            
            if trader_prob > current_mid + edge_threshold:
                # Bullish: Buy YES
                price = min(99, int(trader_prob))
                order = Order(
                    agent_id=trader.agent_name,
                    market_id=self.market.id,
                    side=OrderSide.YES,
                    price=price,
                    quantity=qty
                )
                self.orderbook.place_order(order)
                logger.info(f"[MANAGER] {trader.agent_name} placed YES@{price} (pred={trader_prob})")
                
            elif trader_prob < current_mid - edge_threshold:
                # Bearish: Buy NO
                price = min(99, int(100 - trader_prob))
                order = Order(
                    agent_id=trader.agent_name,
                    market_id=self.market.id,
                    side=OrderSide.NO,
                    price=price,
                    quantity=qty
                )
                self.orderbook.place_order(order)
                logger.info(f"[MANAGER] {trader.agent_name} placed NO@{price} (pred={trader_prob})")
            else:
                logger.info(f"[MANAGER] {trader.agent_name} no trade (pred={trader_prob}, mid={current_mid})")
                
        except Exception as e:
            logger.error(f"[MANAGER] Trader execution failed: {e}")
