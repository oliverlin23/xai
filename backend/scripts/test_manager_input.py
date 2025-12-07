#!/usr/bin/env python3
"""
Test script to verify the data flow from Superforecaster → Manager.

This script:
1. Runs the SynthesisAgent with mock factor data
2. Prints the exact prediction_result dict
3. Shows what the Manager would receive
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.synthesis import SynthesisAgent
from app.manager.market_maker import AvellanedaStoikovMM, MMConfig
from app.manager.manager import SimulationManager


async def test_synthesis_output():
    """Run SynthesisAgent and inspect the output."""
    
    print("=" * 70)
    print("STEP 1: Run SynthesisAgent with mock data")
    print("=" * 70)
    
    # Mock factors (simulating what Phase 1-3 would produce)
    mock_factors = [
        {
            "name": "Economic Indicators",
            "importance_score": 9,
            "research_summary": "GDP growth projections suggest 2.5% growth. Unemployment at 3.8%."
        },
        {
            "name": "Political Climate",
            "importance_score": 8,
            "research_summary": "Current polling shows 52% approval rating. Election in 6 months."
        },
        {
            "name": "Market Sentiment",
            "importance_score": 7,
            "research_summary": "VIX at 18, indicating moderate volatility expectations."
        }
    ]
    
    # Create agent
    agent = SynthesisAgent(session_id="test-session-001")
    
    # Mock input data
    input_data = {
        "question_text": "Will the S&P 500 be higher on December 31, 2025 than it was on January 1, 2025?",
        "question_type": "binary",
        "factors": mock_factors,
        "research": {"factors": mock_factors}
    }
    
    print(f"\nQuestion: {input_data['question_text']}")
    print(f"Factors provided: {len(mock_factors)}")
    print("\nCalling SynthesisAgent.execute()...")
    print("-" * 70)
    
    try:
        # Execute the agent
        result = await agent.execute(input_data)
        
        print("\n" + "=" * 70)
        print("STEP 2: Inspect prediction_result (raw output from agent)")
        print("=" * 70)
        
        print(f"\nResult type: {type(result)}")
        print(f"Result keys: {list(result.keys())}")
        print("\nFull prediction_result dict:")
        print(json.dumps(result, indent=2, default=str))
        
        print("\n" + "=" * 70)
        print("STEP 3: Extract values for Manager")
        print("=" * 70)
        
        # Extract exactly how Manager does it
        prediction_probability = result.get("prediction_probability", 0.5)
        confidence = result.get("confidence", 0.5)
        
        print(f"\nprediction_probability = result.get('prediction_probability', 0.5)")
        print(f"  → {prediction_probability} (type: {type(prediction_probability).__name__})")
        
        print(f"\nconfidence = result.get('confidence', 0.5)")
        print(f"  → {confidence} (type: {type(confidence).__name__})")
        
        print("\n" + "=" * 70)
        print("STEP 4: Initialize Market Maker with these values")
        print("=" * 70)
        
        mm = AvellanedaStoikovMM(
            prediction_probability=prediction_probability,
            confidence=confidence,
            config=MMConfig(terminal_time=60.0)
        )
        
        print(f"\nMarket Maker State:")
        print(f"  mid_price = {mm.mid_price:.2f} cents (from probability {prediction_probability})")
        print(f"  sigma = {mm.sigma:.4f} (from confidence {confidence})")
        
        # Get initial quotes
        bid, ask = mm.get_quotes(current_time=0.0)
        print(f"\nInitial Quotes (t=0):")
        print(f"  Bid: {bid} cents")
        print(f"  Ask: {ask} cents")
        print(f"  Spread: {ask - bid} cents")
        
        print("\n" + "=" * 70)
        print("SUCCESS: Data flow verified!")
        print("=" * 70)
        
        return result
        
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_with_mock_result():
    """Test Manager with a mock prediction_result (no API call)."""
    
    print("\n" + "=" * 70)
    print("BONUS: Test Manager initialization with mock data")
    print("=" * 70)
    
    # Simulate what Superforecaster would output
    mock_prediction_result = {
        "prediction": "Yes",
        "prediction_probability": 0.68,
        "confidence": 0.75,
        "reasoning": "Based on historical trends and current economic indicators...",
        "key_factors": ["Economic Growth", "Market Sentiment", "Fed Policy"]
    }
    
    print("\nMock prediction_result:")
    print(json.dumps(mock_prediction_result, indent=2))
    
    # This is exactly what the Manager does
    manager = SimulationManager(
        session_id="mock-test-001",
        question="Will the S&P 500 be higher at year end?",
        prediction_result=mock_prediction_result,
        duration_seconds=30,
        time_step=1.0
    )
    
    print(f"\nManager initialized:")
    print(f"  prediction_probability: {manager.prediction_probability}")
    print(f"  confidence: {manager.confidence}")
    print(f"  MM mid_price: {manager.mm.mid_price:.2f}")
    print(f"  MM sigma: {manager.mm.sigma:.4f}")
    
    bid, ask = manager.mm.get_quotes(0.0)
    print(f"  Initial quotes: Bid={bid}, Ask={ask}")


if __name__ == "__main__":
    print("\n🧪 Testing Superforecaster → Manager Data Flow\n")
    
    # Run the actual API test
    result = asyncio.run(test_synthesis_output())
    
    if result:
        # Also show mock example
        asyncio.run(test_with_mock_result())

