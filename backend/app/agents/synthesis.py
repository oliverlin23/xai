"""
Phase 4: Synthesis Agent (Agent 24)
Combines all research into final prediction
"""
from typing import Dict, Any, Optional
from app.agents.base import BaseAgent
from app.agents.prompts import get_synthesis_prompt, FORECASTER_CLASSES
from app.schemas import PredictionOutput


class SynthesisAgent(BaseAgent):
    """Agent 24: Prediction synthesizer"""
    
    def __init__(self, session_id: Optional[str] = None, forecaster_class: str = "balanced"):
        """
        Initialize synthesis agent with optional forecaster class.
        
        Args:
            session_id: Session ID for logging
            forecaster_class: One of "conservative", "momentum", "historical", "realtime", "balanced"
        """
        if forecaster_class not in FORECASTER_CLASSES:
            raise ValueError(f"Unknown forecaster_class: {forecaster_class}. Must be one of {list(FORECASTER_CLASSES.keys())}")
        
        system_prompt = get_synthesis_prompt(forecaster_class)
        class_info = FORECASTER_CLASSES[forecaster_class]
        
        super().__init__(
            agent_name=f"synthesizer_{forecaster_class}",
            phase="synthesis",
            system_prompt=system_prompt,
            output_schema=PredictionOutput,
            session_id=session_id
        )
        
        self.forecaster_class = forecaster_class
        self.class_info = class_info
    
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build user message with all research data"""
        question_text = input_data.get("question_text", "")
        question_type = input_data.get("question_type", "binary")
        factors = input_data.get("factors", [])
        research_data = input_data.get("research", {})
        
        # Extract binary options from question
        # For binary questions, default to Yes/No, but try to infer from question structure
        if question_type == "binary":
            binary_options = ["Yes", "No"]
            # Try to extract explicit options if question format is "X or Y?"
            # For questions like "Will X happen?", use Yes/No
            # For questions with explicit options, extract them
            question_lower = question_text.lower().strip()
            if " or " in question_lower:
                # Try to extract options from "X or Y?" format
                parts = question_lower.split(" or ")
                if len(parts) == 2:
                    # Extract the options (may need cleaning)
                    opt1 = parts[0].split()[-1].strip("?")
                    opt2 = parts[1].strip("?")
                    if opt1 and opt2 and len(opt1) < 50 and len(opt2) < 50:
                        binary_options = [opt1.capitalize(), opt2.capitalize()]
        else:
            binary_options = None
        
        # Format factors with research
        factors_text = ""
        for factor in factors:
            name = factor.get("name", "Unknown")
            importance = factor.get("importance_score", "N/A")
            research = factor.get("research_summary", "No research available")
            
            factors_text += f"""
Factor: {name} (Importance: {importance}/10)
Research Summary:
{research}
---
"""
        
        binary_options_text = ""
        if question_type == "binary" and binary_options:
            binary_options_text = f"""
BINARY OPTIONS (you must choose exactly one):
- Option 1: {binary_options[0]}
- Option 2: {binary_options[1]}

Your prediction field MUST be exactly "{binary_options[0]}" or "{binary_options[1]}" - no variations.

"""
        
        return f"""Forecasting Question: {question_text}
Question Type: {question_type}
{binary_options_text}Research Summary for Top Factors:
{factors_text}

Synthesize all this research into a coherent prediction.
Apply superforecasting principles:
- Base rates and outside view
- Break down complex questions  
- Consider multiple perspectives
- Express uncertainty calibrated to evidence

Provide:
1. A prediction that is exactly one of the binary options above
2. prediction_probability (0-1): The probability of the event occurring
3. confidence (0-1): Your confidence in that probability estimate, based on evidence quality, thoroughness, and consistency
4. Detailed reasoning that explains both the probability and your confidence level
5. List of key factors that influenced your prediction

Remember: prediction_probability answers "What's the chance?" and confidence answers "How sure are you about that chance?"
"""

