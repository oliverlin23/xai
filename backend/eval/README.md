# Evaluation Set

This directory contains evaluation sets and scripts for testing the superforecasting system.

## Kalshi Eval Set

The `kalshi_eval_set.json` file contains 5 questions from Kalshi prediction markets with ground truth probabilities:

1. **Nicolas Maduro out of office by end of 2025** - 13% ground truth
2. **Fed rate cut in December** - 90% ground truth
3. **Abelardo de la Espriella wins Colombia election** - 35% ground truth
4. **NVIDIA largest company by June 2026** - 50% ground truth
5. **OpenAI IPO by end of 2026** - 33% ground truth

## Running Evaluations

### Basic Usage

```bash
cd backend
python eval/run_eval.py
```

This will:
- Load the Kalshi eval set
- Run forecasts for all 5 questions **in parallel** (much faster!)
- Calculate Brier scores and calibration errors
- Save results to `eval_results.json`

**Note:** Forecasts run concurrently by default, which significantly speeds up evaluation. Use `--max-concurrent` to limit parallelism if needed (e.g., for rate limiting).

### Custom Agent Counts

Configure agents for each phase:

```bash
python eval/run_eval.py --phase-1-count 5 --phase-2-count 2 --phase-3-count 5 --phase-4-count 1
```

Defaults:
- Phase 1 (Discovery): 5 agents
- Phase 2 (Validation): 2 agents (validator + rating_consensus)
- Phase 3 (Research): 5 agents
- Phase 4 (Synthesis): 1 agent (always 1)

### Limit Number of Questions

Test only a subset of the eval set:

```bash
python eval/run_eval.py --num-questions 3
```

This will test only the first 3 questions from the eval set.

### Limit Concurrency

By default, all forecasts run in parallel. To limit concurrent executions (useful for rate limiting):

```bash
python eval/run_eval.py --max-concurrent 2
```

### Custom Output File

```bash
python eval/run_eval.py --output my_results.json
```

### Custom Eval Set

```bash
python eval/run_eval.py --eval-file custom_eval_set.json
```

## Metrics

The evaluation script calculates:

- **Brier Score**: Measures prediction accuracy (lower is better, 0 = perfect)
  - Formula: `(predicted_prob - actual_outcome)²`
  - Actual outcome is 1 if ground truth ≥ 0.5, else 0

- **Calibration Error**: Measures how far off predicted probability is from ground truth
  - Formula: `|predicted_prob - ground_truth_prob|`
  - Lower is better

## Output Format

The results JSON includes:
- Summary statistics (mean Brier score, mean calibration error, etc.)
- Individual results for each question
- Session IDs for each forecast
- Token usage and duration metrics

## Example Output

```json
{
  "eval_set": "Kalshi Market Predictions Eval Set",
  "eval_date": "2025-01-27T...",
  "summary": {
    "total_questions": 5,
    "successful_forecasts": 5,
    "mean_brier_score": 0.1234,
    "mean_calibration_error": 0.1567,
    "total_tokens": 125000,
    "mean_duration_seconds": 45.2
  },
  "results": [...]
}
```

