# Forecaster Classes

The synthesis agent can now operate in 5 different "personality" modes, each with distinct approaches to forecasting.

## Available Classes

### 1. `conservative` - Conservative Institutional Trader
**Description:** This institutional trader has a strong research foundation and relies heavily on historical theses, generally less tech-pilled and does not rely on live-time updates as frequently. Prefers conservative probabilities and requires strong evidence before deviating from base rates.

**Traits:**
- Risk-averse: Requires higher confidence before making extreme probability estimates
- Historical focus: Heavily weights historical patterns and base rates over recent news
- Conservative calibration: Tends to moderate probabilities toward 0.5 unless evidence is overwhelming
- Evidence threshold: Needs multiple independent sources before moving away from base rates
- Stability preference: Less reactive to breaking news or volatile current data

### 2. `momentum` - Aggressive Momentum Trader
**Description:** This trader focuses on momentum and trend continuation, more willing to take extreme positions when signals align. Prioritizes recent directional shifts and is comfortable with probabilities near 0 or 1 when trends are strong.

**Traits:**
- Momentum-driven: Emphasizes recent trends and directional changes over historical patterns
- Extreme positioning: Comfortable with probabilities near 0.0 or 1.0 when signals align
- Trend continuation: Looks for patterns that suggest continuation rather than mean reversion
- Reactive: More responsive to breaking news and current data shifts
- Confidence in trends: Higher confidence when multiple factors show consistent directional momentum

### 3. `historical` - Historical Pattern Analyst
**Description:** Deep focus on historical trends, base rates, and long-term patterns. This analyst believes history rhymes and uses extensive historical context to inform predictions, often discounting recent anomalies in favor of established patterns.

**Traits:**
- Historical emphasis: Prioritizes long-term patterns and base rates over recent events
- Pattern recognition: Looks for historical analogs and similar past situations
- Base rate anchor: Strongly anchors to historical frequencies before adjusting for specifics
- Long-term view: Considers multi-year or multi-decade trends more than recent volatility
- Skeptical of anomalies: Treats recent outliers with caution, preferring established patterns

### 4. `realtime` - Current Data Specialist
**Description:** Prioritizes real-time information, breaking news, and current market conditions. This specialist believes the most recent data is most predictive and reacts quickly to new information, often updating probabilities based on latest developments.

**Traits:**
- Real-time focus: Heavily weights the most recent data and breaking news
- Current conditions: Prioritizes present-day factors over historical patterns
- Rapid updates: Willing to significantly revise probabilities based on new information
- News sensitivity: More responsive to recent developments and current events
- Temporal recency: Values information recency as a key indicator of relevance

### 5. `balanced` - Balanced Synthesizer (Default)
**Description:** Default balanced approach that weighs historical patterns, current data, and evidence quality equally. Uses standard superforecasting principles without strong bias toward any particular information type.

**Traits:**
- Balanced weighting: Equally considers historical patterns and current data
- Evidence-based: Makes decisions primarily on evidence quality and consistency
- Standard calibration: Uses typical superforecasting calibration principles
- No strong bias: Doesn't systematically favor one type of information over another
- Comprehensive synthesis: Integrates all available information sources equally

## Usage

### API Request

**Basic usage (uses forecaster class defaults):**
```json
POST /api/forecasts
{
    "question_text": "Will X happen?",
    "question_type": "binary",
    "forecaster_class": "conservative"  // Optional, defaults to "balanced"
}
```

**With custom agent counts:**
```json
POST /api/forecasts
{
    "question_text": "Will X happen?",
    "question_type": "binary",
    "forecaster_class": "conservative",
    "agent_counts": {
        "phase_1_discovery": 8,
        "phase_2_validation": 2,
        "phase_3_historical": 7,  // Historical research agents
        "phase_3_current": 3,     // Current research agents
        "phase_4_synthesis": 1
    }
}
```

**Backward compatibility (phase_3_research splits 50/50):**
```json
POST /api/forecasts
{
    "question_text": "Will X happen?",
    "agent_counts": {
        "phase_3_research": 10  // Will split into 5 historical + 5 current
    }
}
```

### Default Agent Counts by Class

| Class | Phase 1 | Phase 2 | Phase 3 Historical | Phase 3 Current | Phase 4 | Total |
|-------|---------|---------|-------------------|-----------------|---------|-------|
| **conservative** | 8 | 2 | 7 | 3 | 1 | 21 |
| **momentum** | 12 | 2 | 3 | 7 | 1 | 25 |
| **historical** | 10 | 2 | 8 | 2 | 1 | 23 |
| **realtime** | 10 | 2 | 2 | 8 | 1 | 23 |
| **balanced** | 10 | 2 | 5 | 5 | 1 | 23 |

### Python Code

```python
from app.agents.prompts import FORECASTER_CLASSES, get_synthesis_prompt

# List all available classes
for class_id, info in FORECASTER_CLASSES.items():
    print(f"{class_id}: {info['name']}")
    print(f"  {info['description']}\n")

# Get prompt for a specific class
prompt = get_synthesis_prompt("conservative")
```

### Programmatic Access

```python
from app.agents.synthesis import SynthesisAgent

# Create synthesis agent with specific class
agent = SynthesisAgent(
    session_id="session-123",
    forecaster_class="momentum"
)
```

## How It Works

Each forecaster class modifies the synthesis agent's system prompt to emphasize different aspects:

1. **Conservative**: Adds guidance to be more risk-averse and require stronger evidence
2. **Momentum**: Emphasizes trend continuation and recent directional changes
3. **Historical**: Prioritizes historical patterns and base rates
4. **Realtime**: Focuses on most recent data and breaking news
5. **Balanced**: Uses standard superforecasting approach (no modifications)

The core superforecasting methodology remains the same - the class only influences *how* evidence is weighted and interpreted, not *whether* rigorous analysis is performed.

## Choosing a Class

- Use **conservative** for: Long-term predictions, stable markets, when you want more cautious estimates
- Use **momentum** for: Short-term predictions, trending markets, when recent shifts are important
- Use **historical** for: Questions with strong historical precedents, when base rates are well-established
- Use **realtime** for: Fast-moving situations, breaking news events, when current conditions dominate
- Use **balanced** for: General use, when you want equal weighting of all factors

