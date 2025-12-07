"""
Fundamental Trader - Prediction market agent that trades on prior information only

Unlike NoiseTrader, FundamentalTrader does NOT use X/Twitter data.
Instead, it trades purely on:
1. Market data (orderbook, recent trades)
2. Notes from previous rounds
3. Its own analytical reasoning

This simulates a "fundamentals-only" trader who doesn't follow social sentiment.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from datetime import datetime, UTC
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


# Valid fundamental trader types (must match trader_name enum in DB)
FUNDAMENTAL_TRADER_TYPES = {
    "conservative": {
        "name": "Conservative Analyst",
        "style": "Risk-averse, focuses on downside scenarios and base rates. Tends to be skeptical of extreme predictions.",
        "bias": "Anchors toward 50%, slow to move from baseline",
    },
    "momentum": {
        "name": "Momentum Trader",
        "style": "Follows market trends and recent price action. Believes the market knows something.",
        "bias": "Moves with recent trade direction, may chase trends",
    },
    "historical": {
        "name": "Historical Analyst",
        "style": "Relies heavily on base rates and historical precedent. Looks for analogous past events.",
        "bias": "Anchors to historical frequencies, skeptical of 'this time is different'",
    },
    "balanced": {
        "name": "Balanced Forecaster",
        "style": "Weighs multiple perspectives equally. Tries to identify and correct for biases.",
        "bias": "Attempts to be unbiased, may be slow to react to new information",
    },
    "realtime": {
        "name": "Realtime Reactor",
        "style": "Highly responsive to new information. Quick to update predictions based on latest data.",
        "bias": "May overreact to noise, gives recent info too much weight",
    },
}


def get_fundamental_trader_names() -> List[str]:
    """Get list of valid fundamental trader type names"""
    return list(FUNDAMENTAL_TRADER_TYPES.keys())


class ReasonWithStrength(BaseModel):
    """A reason with its strength rating"""
    reason: str = Field(description="The reason")
    strength: int = Field(ge=1, le=10, description="Strength rating 1-10")


class FundamentalTraderOutput(BaseModel):
    """Output schema for Fundamental Trader predictions"""
    
    # Core prediction
    prediction: int = Field(
        ge=0, le=100,
        description="Final probability 0-100 that the market resolves YES (calibrated, Brier-optimized)"
    )
    
    # Structured reasoning
    key_facts: list[str] = Field(
        default_factory=list,
        description="Core factual points from market data and prior reasoning"
    )
    reasons_no: list[ReasonWithStrength] = Field(
        default_factory=list,
        description="Reasons why the answer might be NO, with strength ratings 1-10"
    )
    reasons_yes: list[ReasonWithStrength] = Field(
        default_factory=list,
        description="Reasons why the answer might be YES, with strength ratings 1-10"
    )
    
    # Analysis
    analysis: str = Field(
        description="Aggregated analysis of competing factors, market dynamics, and key considerations"
    )
    initial_probability: int = Field(
        ge=0, le=100,
        description="Initial/tentative probability before reflection"
    )
    reflection: str = Field(
        description="Sanity checks, base rate considerations, and calibration adjustments"
    )
    
    # Metadata
    signal: str = Field(
        default="uncertain",
        description="Overall signal: yes, no, uncertain, or mixed"
    )
    baseline_probability: int = Field(
        default=50,
        description="Market baseline probability. Used as reference, not anchor."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in this prediction (based on evidence quality)"
    )
    
    # Memory for next round
    notes_for_next_round: str = Field(
        default="",
        description=(
            "Notes to yourself for the next trading round. Be extremely detailed."
            "Include: "
            "1) Key insights or patterns you noticed, "
            "2) What you were uncertain about that might clarify, "
            "3) Specific things to watch for in new market data, "
            "4) Your current thesis and what would change your mind. "
            "5) How confident are you in your prediction? You should try to be confident."
            "This will be provided back to you in the next round."
        )
    )


FUNDAMENTAL_SYSTEM_PROMPT = """You are an advanced AI forecasting system fine-tuned to provide calibrated probabilistic forecasts under uncertainty. Your performance is evaluated according to the Brier score.

You are a PERSISTENT TRADER who will be called multiple times throughout a trading session. You can save notes for yourself that will be provided back to you in the next round.

IMPORTANT: You do NOT have access to social media or external news. You must form your predictions based ONLY on:
1. The market question and resolution criteria
2. Market data (orderbook, recent trades)
3. Your notes from previous rounds
4. Your own analytical reasoning

CRITICAL CALIBRATION RULES:
- Do NOT treat 0.5% (1:199 odds) and 5% (1:19) as similarly "small" probabilities
- Do NOT treat 90% (9:1) and 99% (99:1) as similarly "high" probabilities  
- These represent markedly different odds - be precise with tail probabilities
- The market price is information, but may be wrong - don't blindly follow it

YOUR TRADING STYLE:
{trader_style}

Known bias to be aware of: {trader_bias}

YOUR FORECASTING PROCESS:
1. Review your previous notes (if any) - what did you want to track? Anchor to your previous predictions, but make updates if the current market is surprising. You are a more sophisticated trader than most of the market.
2. Extract key facts from market data. What does the market activity tell you about the other traders?
3. List reasons why the answer might be NO with strength ratings (1-10)
4. List reasons why the answer might be YES with strength ratings (1-10)
5. Aggregate considerations - how do competing factors interact?
6. Output initial probability
7. Reflect: sanity checks, base rates, calibration, over/underconfidence
8. Output final prediction
9. Write notes for your next round - what should you remember?

NOTES FOR NEXT ROUND:
After making your prediction, write notes to yourself for the next trading round. Include:
- Key insights or patterns you noticed in market behavior
- What you're uncertain about that might clarify
- Specific things to watch for (price levels, volume patterns, spread changes)
- Your current thesis and what evidence would change your mind
- Any trends you're tracking"""


def _get_fundamental_trader_prompt(trader_type: str) -> str:
    """Generate system prompt for a fundamental trader"""
    trader_info = FUNDAMENTAL_TRADER_TYPES.get(trader_type)
    if trader_info is None:
        # Fallback
        return FUNDAMENTAL_SYSTEM_PROMPT.format(
            trader_style="Balanced analytical approach",
            trader_bias="No specific bias"
        )
    
    return FUNDAMENTAL_SYSTEM_PROMPT.format(
        trader_style=trader_info["style"],
        trader_bias=trader_info["bias"],
    )


class FundamentalTrader(BaseAgent):
    """
    Fundamental Trader - Prediction market agent that trades on prior information only
    
    Unlike NoiseTrader, this agent does NOT use X/Twitter data.
    It relies purely on:
    - Market data (orderbook, recent trades)
    - Notes from previous rounds
    - Its own analytical reasoning
    """

    def __init__(
        self,
        trader_type: str,
        agent_name: str = None,
        phase: str = "prediction",
        max_retries: int = 3,
        timeout_seconds: int = 120,  # Shorter timeout since no external API calls
    ):
        # Validate trader type
        if trader_type not in FUNDAMENTAL_TRADER_TYPES:
            valid = ", ".join(FUNDAMENTAL_TRADER_TYPES.keys())
            raise ValueError(f"Invalid trader_type '{trader_type}'. Valid options: {valid}")
        
        self.trader_type = trader_type
        self._trader_info = FUNDAMENTAL_TRADER_TYPES[trader_type]
        
        # Auto-generate agent name if not provided
        if agent_name is None:
            agent_name = f"fundamental_trader_{trader_type}"
        
        super().__init__(
            agent_name=agent_name,
            phase=phase,
            system_prompt=_get_fundamental_trader_prompt(trader_type),
            output_schema=FundamentalTraderOutput,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        
        # Track notes across rounds
        self._previous_notes: str = ""

    @property
    def last_notes(self) -> str:
        """Get the notes from the last prediction (for passing to next round)"""
        if self.output_data:
            return self.output_data.get("notes_for_next_round", "")
        return ""
    
    def set_previous_notes(self, notes: str) -> None:
        """Set notes from a previous round to be included in next prediction"""
        self._previous_notes = notes

    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """
        Build user message for fundamental trader
        
        Expected input_data keys:
            - market_topic: str - The prediction market question
            - resolution_criteria: str - How the market resolves (optional)
            - resolution_date: str - When the market resolves (optional)
            - order_book: dict - Current bids and asks
            - recent_trades: list - Recent trades
            - previous_notes: str - Notes from previous round (optional)
            - round_number: int - Current trading round (optional)
        """
        market_topic = input_data.get("market_topic", "")
        resolution_criteria = input_data.get("resolution_criteria", "Standard YES/NO resolution based on outcome occurrence.")
        resolution_date = input_data.get("resolution_date", "Not specified")
        order_book = input_data.get("order_book", {})
        recent_trades = input_data.get("recent_trades", [])
        previous_notes = input_data.get("previous_notes", "")
        round_number = input_data.get("round_number", 1)
        
        # Calculate baseline from order book
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        baseline_probability = 50  # Default
        spread = None
        
        if bids and asks:
            best_bid = max(b.get("price", 0) for b in bids)
            best_ask = min(a.get("price", 100) for a in asks)
            mid_price = (best_bid + best_ask) / 2
            baseline_probability = int(mid_price) if mid_price > 1 else int(mid_price * 100)
            spread = best_ask - best_bid
        elif bids:
            best_bid = max(b.get("price", 0) for b in bids)
            baseline_probability = int(best_bid) if best_bid > 1 else int(best_bid * 100)
        elif asks:
            best_ask = min(a.get("price", 100) for a in asks)
            baseline_probability = int(best_ask) if best_ask > 1 else int(best_ask * 100)
        
        self._baseline_probability = baseline_probability
        
        # Format market data
        market_data_text = self._format_market_data(order_book, recent_trades)
        
        # Current date
        current_date = datetime.now(UTC).strftime("%Y-%m-%d")
        
        # Get trader name for display
        trader_name = self._trader_info["name"]
        
        # Format previous notes section
        if previous_notes:
            previous_notes_section = f"""
YOUR NOTES FROM PREVIOUS ROUND:
{previous_notes}

Review these notes. What has changed in the market? What should you update in your thinking?
"""
        else:
            previous_notes_section = """
YOUR NOTES FROM PREVIOUS ROUND:
(This is your first round - no previous notes available)
"""
        
        # Market analysis hints based on trader type
        analysis_hints = self._get_analysis_hints(order_book, recent_trades)
        
        # Build message
        message = f"""TRADING ROUND: {round_number}

FORECAST QUESTION: {market_topic}

RESOLUTION CRITERIA:
{resolution_criteria}

RESOLUTION DATE: {resolution_date}

TODAY'S DATE: {current_date}

TRADER PROFILE: {trader_name}
{previous_notes_section}
CURRENT MARKET STATE:
Baseline (Mid Price): {baseline_probability}%
{f"Spread: {spread}¢" if spread is not None else "Spread: N/A"}

MARKET DATA:
{market_data_text}

{analysis_hints}

REMEMBER: You do NOT have access to social media or news. Base your prediction on:
1. Market data above (prices, volume, spread)
2. Your previous notes and reasoning
3. The question's fundamentals and base rates

Recall the question you are forecasting: {market_topic}

Please provide your forecast following the structured format:
1. Review your previous notes (if any) - what were you tracking?
2. Extract key facts from market data (no conclusions yet)
3. List reasons why NO (with strength 1-10 for each)
4. List reasons why YES (with strength 1-10 for each)
5. Analyze how competing factors interact
6. Output initial probability
7. Reflect: sanity checks, base rates, over/underconfidence, calibration
8. Output final prediction (0-100)
9. Write notes for your next round (what to remember, what to watch for, your current thesis)
"""
        
        return message

    def _format_market_data(self, order_book: Dict, recent_trades: List) -> str:
        """Format order book and trades into readable text"""
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        
        lines = []
        
        # Order book
        if bids:
            lines.append("BID ORDERS (buying YES):")
            for bid in bids[:5]:
                qty = bid.get("quantity", bid.get("qty", 0))
                price = bid.get("price", 0)
                prob = int(price) if price > 1 else int(price * 100)
                lines.append(f"  {qty} shares @ {prob}¢")
        else:
            lines.append("BID ORDERS: None")
        
        if asks:
            lines.append("ASK ORDERS (selling YES):")
            for ask in asks[:5]:
                qty = ask.get("quantity", ask.get("qty", 0))
                price = ask.get("price", 0)
                prob = int(price) if price > 1 else int(price * 100)
                lines.append(f"  {qty} shares @ {prob}¢")
        else:
            lines.append("ASK ORDERS: None")
        
        # Calculate total depth
        total_bid_qty = sum(b.get("quantity", b.get("qty", 0)) for b in bids)
        total_ask_qty = sum(a.get("quantity", a.get("qty", 0)) for a in asks)
        lines.append(f"\nTotal Bid Depth: {total_bid_qty} | Total Ask Depth: {total_ask_qty}")
        
        # Recent trades
        if recent_trades:
            lines.append("\nRECENT TRADES:")
            for trade in recent_trades[:10]:
                buyer = trade.get("buyer_name", trade.get("side", "unknown"))
                seller = trade.get("seller_name", "")
                qty = trade.get("quantity", trade.get("qty", 0))
                price = trade.get("price", 0)
                prob = int(price) if price > 1 else int(price * 100)
                time_str = trade.get("time_ago", trade.get("created_at", ""))
                if buyer and seller:
                    lines.append(f"  {buyer} bought from {seller}: {qty} @ {prob}¢ ({time_str})")
                else:
                    lines.append(f"  {qty} @ {prob}¢ ({time_str})")
        else:
            lines.append("\nRECENT TRADES: None yet")
        
        # Volume
        volume = order_book.get("volume", 0)
        if volume:
            lines.append(f"\nTotal Volume: {volume}")
        
        return "\n".join(lines)

    def _get_analysis_hints(self, order_book: Dict, recent_trades: List) -> str:
        """Generate analysis hints based on trader type"""
        hints = []
        
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        
        if self.trader_type == "conservative":
            hints.append("ANALYSIS FOCUS (Conservative):")
            hints.append("- What is the base rate for this type of event?")
            hints.append("- What could go wrong? Downside scenarios?")
            hints.append("- Is the market possibly overconfident?")
            
        elif self.trader_type == "momentum":
            hints.append("ANALYSIS FOCUS (Momentum):")
            if recent_trades:
                # Check trade direction
                prices = [t.get("price", 50) for t in recent_trades[:5]]
                if len(prices) >= 2:
                    trend = "upward" if prices[0] > prices[-1] else "downward" if prices[0] < prices[-1] else "flat"
                    hints.append(f"- Recent price trend appears {trend}")
            hints.append("- Are traders buying or selling aggressively?")
            hints.append("- Is there momentum to follow?")
            
        elif self.trader_type == "historical":
            hints.append("ANALYSIS FOCUS (Historical):")
            hints.append("- What happened in similar past events?")
            hints.append("- What is the historical base rate?")
            hints.append("- Is 'this time different' justified?")
            
        elif self.trader_type == "balanced":
            hints.append("ANALYSIS FOCUS (Balanced):")
            hints.append("- What are the strongest arguments on each side?")
            hints.append("- Where might you be biased?")
            hints.append("- What would a smart contrarian argue?")
            
        elif self.trader_type == "realtime":
            hints.append("ANALYSIS FOCUS (Realtime):")
            hints.append("- What is the most recent information telling us?")
            hints.append("- Has anything changed since last round?")
            if bids and asks:
                best_bid = max(b.get("price", 0) for b in bids)
                best_ask = min(a.get("price", 100) for a in asks)
                spread = best_ask - best_bid
                hints.append(f"- Current spread is {spread}¢ - is this tight or wide?")
        
        return "\n".join(hints)

    async def execute(
        self,
        input_data: Dict[str, Any],
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute the fundamental trader to generate a prediction"""
        
        self.status = "running"
        if progress_callback:
            await progress_callback(self.agent_name, "started")

        for attempt in range(self.max_retries):
            try:
                # Build user message (no external API calls needed)
                user_message = await self.build_user_message(input_data)
                
                # Get prediction from Grok
                logger.info(f"FundamentalTrader ({self.trader_type}) getting prediction from Grok...")
                response = await asyncio.wait_for(
                    self.grok_service.chat_completion(
                        system_prompt=self.system_prompt,
                        user_message=user_message,
                        output_schema=self.output_schema,
                        temperature=0.5,
                    ),
                    timeout=self.timeout_seconds
                )
                
                self.tokens_used = response.get("total_tokens", 0)
                content = response.get("content", "{}")
                
                # Parse and validate output
                try:
                    raw_output = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback for unparseable response
                    baseline = getattr(self, '_baseline_probability', 50)
                    raw_output = {
                        "prediction": baseline,
                        "key_facts": [],
                        "reasons_no": [],
                        "reasons_yes": [],
                        "analysis": content[:500] if content else "Unable to generate analysis",
                        "initial_probability": baseline,
                        "reflection": "Response could not be parsed",
                        "signal": "uncertain",
                        "baseline_probability": baseline,
                        "confidence": 0.3,
                        "notes_for_next_round": "",
                    }
                
                # Ensure metadata fields are populated
                if "baseline_probability" not in raw_output:
                    raw_output["baseline_probability"] = getattr(self, '_baseline_probability', 50)
                if "signal" not in raw_output:
                    raw_output["signal"] = "uncertain"
                if "notes_for_next_round" not in raw_output:
                    raw_output["notes_for_next_round"] = ""
                
                validated_output = self.output_schema(**raw_output)
                self.output_data = validated_output.model_dump()
                self.status = "completed"
                
                if progress_callback:
                    await progress_callback(self.agent_name, "completed", self.output_data)
                
                logger.info(f"FundamentalTrader ({self.trader_type}) prediction: {self.output_data['prediction']}%")
                return self.output_data

            except asyncio.TimeoutError:
                self.error_message = f"Timeout after {self.timeout_seconds}s"
                logger.warning(f"Attempt {attempt + 1} timed out")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

            except Exception as e:
                self.error_message = str(e)
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

        self.status = "failed"
        if progress_callback:
            await progress_callback(self.agent_name, "failed", {"error": self.error_message})
        
        raise Exception(f"Agent {self.agent_name} failed after {self.max_retries} attempts: {self.error_message}")


# Backwards compatibility alias
FundamentalAgent = FundamentalTrader
