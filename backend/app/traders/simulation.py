"""
Trading Simulation Orchestrator

Manages 18 trading agents in a continuous simulation:
- 5 FundamentalTrader (conservative, momentum, historical, balanced, realtime)
- 9 NoiseTrader (9 X spheres of influence)
- 4 UserAgent (oliver, owen, skylar, tyler)

Each agent reads/writes notes from trader_state_live.system_prompt for persistence.
Trades are recorded in the trades table for real-time frontend visibility.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from app.traders.fundamental_agent import FundamentalTrader, get_fundamental_trader_names
from app.traders.noise_agent import NoiseTrader
from app.traders.user_agent import UserAgent, get_user_agent_names
from app.market import SupabaseMarketMaker
from app.db.repositories import TraderRepository, SessionRepository

logger = logging.getLogger(__name__)

# All available spheres for noise traders
NOISE_TRADER_SPHERES = [
    "eacc_sovereign",
    "america_first", 
    "blue_establishment",
    "progressive_left",
    "optimizer_idw",
    "fintwit_market",
    "builder_engineering",
    "academic_research",
    "osint_intel",
]


class TradingSimulation:
    """
    Orchestrates a continuous trading simulation with 18 agents.
    
    The simulation runs in rounds. Each round:
    1. All agents read their previous notes from DB
    2. All agents get market data (orderbook, recent trades)
    3. All agents make predictions in parallel
    4. All agents place market-making orders
    5. All agents save their notes to DB
    
    The frontend can see trades in real-time via Supabase realtime subscriptions.
    """
    
    def __init__(
        self,
        session_id: str,
        question_text: str,
        resolution_criteria: str = "Standard YES/NO resolution based on outcome occurrence.",
        resolution_date: str = "Not specified",
    ):
        self.session_id = session_id
        self.question_text = question_text
        self.resolution_criteria = resolution_criteria
        self.resolution_date = resolution_date
        
        self._running = False
        self._round_number = 0
        self._agents: Dict[str, Any] = {}
        self._task: Optional[asyncio.Task] = None  # Track the running task
        
        self._market_maker = SupabaseMarketMaker()
        self._trader_repo = TraderRepository()
        self._session_repo = SessionRepository()
        
        logger.info(f"TradingSimulation created for session {session_id}")
    
    async def initialize_agents(self) -> None:
        """
        Create all 18 agents and initialize their trader_state_live records.
        """
        logger.info(f"[SIMULATION] Initializing 18 agents for session {self.session_id}")
        
        # 5 Fundamental Traders
        fundamental_types = get_fundamental_trader_names()
        for trader_type in fundamental_types:
            agent = FundamentalTrader(
                trader_type=trader_type,
                session_id=self.session_id,
                timeout_seconds=120,
            )
            self._agents[f"fundamental_{trader_type}"] = agent
            
            # Ensure trader_state_live record exists (may already exist from superforecasters)
            self._ensure_trader_record(trader_type, "fundamental")
        
        logger.info(f"[SIMULATION] Initialized {len(fundamental_types)} fundamental traders")
        
        # 9 Noise Traders
        for sphere in NOISE_TRADER_SPHERES:
            agent = NoiseTrader(
                sphere=sphere,
                session_id=self.session_id,
                timeout_seconds=300,
                use_semantic_filter=True,
            )
            self._agents[f"noise_{sphere}"] = agent
            
            # Create trader_state_live record
            self._ensure_trader_record(sphere, "noise")
        
        logger.info(f"[SIMULATION] Initialized {len(NOISE_TRADER_SPHERES)} noise traders")
        
        # 4 User Agents
        user_names = get_user_agent_names()
        for user_name in user_names:
            agent = UserAgent(
                name=user_name,
                session_id=self.session_id,
                timeout_seconds=300,
            )
            self._agents[f"user_{user_name}"] = agent
            
            # Create trader_state_live record
            self._ensure_trader_record(user_name, "user")
        
        logger.info(f"[SIMULATION] Initialized {len(user_names)} user agents")
        logger.info(f"[SIMULATION] Total agents: {len(self._agents)}")
    
    def _ensure_trader_record(self, trader_name: str, trader_type: str) -> None:
        """Ensure a trader_state_live record exists for the agent."""
        try:
            existing = self._trader_repo.get_trader(self.session_id, trader_name)
            if not existing:
                self._trader_repo.create({
                    "session_id": self.session_id,
                    "trader_type": trader_type,
                    "name": trader_name,
                    "system_prompt": "",
                })
                logger.debug(f"Created trader record for {trader_name}")
        except Exception as e:
            logger.warning(f"Failed to ensure trader record for {trader_name}: {e}")
    
    async def run_round(self) -> Dict[str, Any]:
        """
        Execute one trading round.
        
        Returns dict with results for each agent.
        """
        self._round_number += 1
        round_start = datetime.now(UTC)
        logger.info(f"[SIMULATION] Starting round {self._round_number}")
        
        # Get current market state
        orderbook = self._market_maker.get_orderbook(self.session_id)
        recent_trades = self._market_maker.get_recent_trades(self.session_id, limit=20)
        
        # Build common input data
        base_input = {
            "market_topic": self.question_text,
            "resolution_criteria": self.resolution_criteria,
            "resolution_date": self.resolution_date,
            "order_book": orderbook,
            "recent_trades": recent_trades,
            "round_number": self._round_number,
        }
        
        results: Dict[str, Any] = {}
        
        # Run all agents in parallel
        async def run_agent(agent_key: str, agent: Any) -> tuple[str, Dict[str, Any]]:
            try:
                input_data = base_input.copy()
                result = await agent.execute(input_data)
                
                # Place market-making orders if prediction available
                prediction = result.get("prediction")
                if prediction is not None and not result.get("skipped"):
                    # Clamp prediction to valid range for market making
                    prediction_cents = max(2, min(98, prediction))
                    
                    mm_result = self._market_maker.place_market_making_orders(
                        session_id=self.session_id,
                        trader_name=agent.trader_name,
                        prediction=prediction_cents,
                        spread=4,
                        quantity=100,
                    )
                    
                    if mm_result.get("error"):
                        logger.warning(f"Market making failed for {agent_key}: {mm_result['error']}")
                    else:
                        trades_count = mm_result.get("trades_count", 0)
                        if trades_count > 0:
                            logger.info(f"[SIMULATION] {agent_key} matched {trades_count} trades")
                
                return agent_key, {"success": True, "prediction": prediction, **result}
            
            except Exception as e:
                logger.error(f"[SIMULATION] Agent {agent_key} failed: {e}")
                return agent_key, {"success": False, "error": str(e)}
        
        # Execute all agents concurrently
        tasks = [run_agent(key, agent) for key, agent in self._agents.items()]
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for item in agent_results:
            if isinstance(item, Exception):
                logger.error(f"[SIMULATION] Task exception: {item}")
            else:
                agent_key, result = item
                results[agent_key] = result
        
        # Log round summary
        round_duration = (datetime.now(UTC) - round_start).total_seconds()
        successful = sum(1 for r in results.values() if r.get("success"))
        skipped = sum(1 for r in results.values() if r.get("skipped"))
        failed = len(results) - successful
        
        logger.info(
            f"[SIMULATION] Round {self._round_number} complete in {round_duration:.1f}s - "
            f"Success: {successful}, Skipped: {skipped}, Failed: {failed}"
        )
        
        return results
    
    async def run_continuous(self, interval_seconds: int = 10) -> None:
        """
        Run continuous trading simulation until stopped.
        
        Args:
            interval_seconds: Seconds between rounds (default 10)
        """
        self._running = True
        # Store reference to current task so stop() can cancel it
        self._task = asyncio.current_task()
        logger.info(f"[SIMULATION] Starting continuous simulation (interval: {interval_seconds}s)")
        
        # Initialize agents if not done
        if not self._agents:
            await self.initialize_agents()
        
        try:
            while self._running:
                try:
                    await self.run_round()
                except asyncio.CancelledError:
                    logger.info("[SIMULATION] Round cancelled")
                    raise  # Re-raise to exit the loop
                except Exception as e:
                    logger.error(f"[SIMULATION] Round failed: {e}")
                
                # Wait before next round
                if self._running:
                    await asyncio.sleep(interval_seconds)
                    
        except asyncio.CancelledError:
            logger.info("[SIMULATION] Simulation cancelled")
        finally:
            self._running = False
            self._task = None
            logger.info("[SIMULATION] Simulation stopped")
    
    def stop(self) -> None:
        """Stop the simulation gracefully by cancelling the running task."""
        logger.info(f"[SIMULATION] Stopping simulation for session {self.session_id}")
        self._running = False
        
        # Cancel the task if it's running
        if self._task is not None and not self._task.done():
            logger.info(f"[SIMULATION] Cancelling task for session {self.session_id}")
            self._task.cancel()
    
    @property
    def is_running(self) -> bool:
        """Check if simulation is currently running."""
        return self._running
    
    @property
    def round_number(self) -> int:
        """Get current round number."""
        return self._round_number
    
    @property
    def agent_count(self) -> int:
        """Get total number of agents."""
        return len(self._agents)
    
    def get_status(self) -> Dict[str, Any]:
        """Get simulation status."""
        return {
            "session_id": self.session_id,
            "running": self._running,
            "round_number": self._round_number,
            "agent_count": len(self._agents),
            "agents": list(self._agents.keys()),
        }


# Global registry of active simulations
ACTIVE_SIMULATIONS: Dict[str, TradingSimulation] = {}


def get_simulation(session_id: str) -> Optional[TradingSimulation]:
    """Get an active simulation by session ID."""
    return ACTIVE_SIMULATIONS.get(session_id)


def register_simulation(simulation: TradingSimulation) -> None:
    """Register a simulation in the global registry."""
    ACTIVE_SIMULATIONS[simulation.session_id] = simulation
    logger.info(f"Registered simulation for session {simulation.session_id}")


def unregister_simulation(session_id: str) -> None:
    """Remove a simulation from the global registry."""
    if session_id in ACTIVE_SIMULATIONS:
        del ACTIVE_SIMULATIONS[session_id]
        logger.info(f"Unregistered simulation for session {session_id}")


def get_all_simulations() -> Dict[str, TradingSimulation]:
    """Get all active simulations."""
    return ACTIVE_SIMULATIONS.copy()
