"""
Evaluation script for running forecasts on the Kalshi eval set
and comparing predictions against ground truth probabilities.
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionRepository
from app.agents.orchestrator import AgentOrchestrator
from app.services.grok import GrokService
from app.schemas import PredictionOutput
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def load_eval_set(eval_file: str = "kalshi_eval_set.json") -> Dict[str, Any]:
    """Load the evaluation set from JSON file"""
    eval_path = Path(__file__).parent / eval_file
    with open(eval_path, "r") as f:
        return json.load(f)


def calculate_brier_score(predicted_prob: float, actual_outcome: bool) -> float:
    """
    Calculate Brier score for a single prediction.
    Lower is better (0 = perfect, 1 = worst)
    """
    return (predicted_prob - (1.0 if actual_outcome else 0.0)) ** 2


def calculate_calibration_error(predicted_prob: float, actual_prob: float) -> float:
    """
    Calculate absolute calibration error.
    Measures how far off the predicted probability is from the ground truth.
    """
    return abs(predicted_prob - actual_prob)


async def run_one_shot_baseline(question_text: str, question_type: str = "binary") -> Dict[str, Any]:
    """Run a one-shot Grok 4.1 baseline prediction (no orchestration)"""
    baseline_start = datetime.now()
    grok_service = GrokService()
    
    # Binary options are always Yes/No for binary questions
    
    # Simplified one-shot prompt based on synthesis agent
    system_prompt = """You are an advanced forecasting model optimized for sharp, well-calibrated probabilistic judgments. Your performance is evaluated by Brier score. You are a superforecaster: you decompose problems, weigh evidence, test competing hypotheses, and state probabilities with conviction when justified.

## CORE PRINCIPLES
- **Evidence-first:** Ground all claims strictly in available information, not pretraining intuition.
- **Structured synthesis:** Decompose the problem into drivers, analyze each, recombine logically.
- **Calibration discipline:** Confidence must track evidence strength. Avoid both overconfidence and unwarranted hedging.
- **Superforecasting methods:** Use outside view, inside view, decomposition, and continual updating.

## OUTPUT FORMAT
Return a JSON object with:
- **prediction:** exactly one of the two binary options provided (character-for-character match)
- **prediction_probability:** float (0.0–1.0) = probability the event occurs
- **confidence:** float (0.0–1.0) = confidence in the accuracy of your probability estimate
- **reasoning:** 300–800 words synthesizing evidence, mechanisms, base rates, and justification
- **key_factors:** 3–7 short labels naming the core drivers

CRITICAL: 
- The prediction field MUST match exactly one of the two binary options provided
- prediction_probability = "What's the chance?" and confidence = "How sure are you about that chance?"
- Both are evidence-based, not politeness-based."""

    user_message = f"""Forecasting Question: {question_text}
Question Type: {question_type}

Binary Options:
- Yes
- No

Provide a calibrated probabilistic forecast. Apply superforecasting principles:
- Base rates and outside view
- Break down complex questions  
- Consider multiple perspectives
- Express uncertainty calibrated to evidence

Provide:
1. A prediction that is exactly one of the binary options above
2. prediction_probability (0-1): The probability of the event occurring
3. confidence (0-1): Your confidence in that probability estimate, based on evidence quality and thoroughness
4. Detailed reasoning that explains both the probability and your confidence level
5. List of key factors that influenced your prediction"""

    try:
        response = await grok_service.chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            output_schema=PredictionOutput,
            temperature=0.7,
            max_tokens=2000,
            enable_web_search=False  # No web search for baseline - pure model knowledge
        )
        
        # Parse the structured output
        import json
        if isinstance(response["content"], str):
            output_data = json.loads(response["content"])
        else:
            output_data = response["content"]
        
        baseline_end = datetime.now()
        baseline_duration = (baseline_end - baseline_start).total_seconds()
        
        return {
            "prediction": output_data.get("prediction", ""),
            "prediction_probability": output_data.get("prediction_probability"),
            "confidence": output_data.get("confidence"),
            "reasoning": output_data.get("reasoning", ""),
            "key_factors": output_data.get("key_factors", []),
            "total_duration_seconds": baseline_duration,
            "total_cost_tokens": response.get("total_tokens", 0),
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"[BASELINE] One-shot baseline failed: {e}", exc_info=True)
        baseline_end = datetime.now()
        baseline_duration = (baseline_end - baseline_start).total_seconds()
        return {
            "prediction": None,
            "prediction_probability": None,
            "confidence": None,
            "reasoning": None,
            "key_factors": [],
            "total_duration_seconds": baseline_duration,
            "total_cost_tokens": 0,
            "status": "failed",
            "error": str(e)
        }


async def run_forecast(question_text: str, question_type: str = "binary", agent_counts: Dict[str, int] = None) -> Dict[str, Any]:
    """Run a single forecast and return the prediction result"""
    forecast_start = datetime.now()
    session_repo = SessionRepository()
    
    # Create session
    session = session_repo.create_session(
        question_text=question_text,
        question_type=question_type
    )
    session_id = session["id"]
    
    logger.info("[EVAL] ┌─ Starting forecast")
    logger.info(f"[EVAL] │  Session ID: {session_id}")
    logger.info(f"[EVAL] │  Question: {question_text}")
    logger.info(f"[EVAL] │  Question Type: {question_type}")
    if agent_counts:
        logger.info(f"[EVAL] │  Agent Config: P1={agent_counts.get('phase_1_discovery')}, "
                   f"P2={agent_counts.get('phase_2_validation')}, "
                   f"P3={agent_counts.get('phase_3_research')}, "
                   f"P4={agent_counts.get('phase_4_synthesis')}")
    logger.info(f"[EVAL] │  Started at: {forecast_start.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run orchestrator
    orchestrator = AgentOrchestrator(session_id, question_text, agent_counts=agent_counts)
    await orchestrator.run()
    
    forecast_end = datetime.now()
    forecast_duration = (forecast_end - forecast_start).total_seconds()
    
    # Get final session data
    final_session = session_repo.find_by_id(session_id)
    if not final_session:
        raise ValueError(f"Session {session_id} not found")
    prediction_result = final_session.get("prediction_result", {})
    
    logger.info(f"[EVAL] │  Completed at: {forecast_end.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"[EVAL] │  Duration: {forecast_duration:.2f}s")
    logger.info(f"[EVAL] │  Tokens: {final_session.get('total_cost_tokens', 0):,}")
    logger.info("[EVAL] └─ Forecast complete")
    
    # Extract prediction_probability from session (new column) or fallback to JSONB
    prediction_probability = final_session.get("prediction_probability")
    if prediction_probability is None:
        prediction_probability = prediction_result.get("prediction_probability")
    
    return {
        "session_id": session_id,
        "prediction": prediction_result.get("prediction"),
        "prediction_probability": prediction_probability,
        "confidence": prediction_result.get("confidence"),
        "reasoning": prediction_result.get("reasoning"),
        "key_factors": prediction_result.get("key_factors", []),
        "total_duration_seconds": prediction_result.get("total_duration_seconds"),
        "total_cost_tokens": final_session.get("total_cost_tokens", 0),
        "status": final_session.get("status")
    }


async def evaluate_question(
    question: Dict[str, Any],
    agent_counts: Dict[str, int] = None,
    question_num: int = None,
    total_questions: int = None,
    run_baseline: bool = True
) -> Dict[str, Any]:
    """Evaluate a single question and return results (orchestrated + baseline)"""
    question_id = question["id"]
    eval_start = datetime.now()
    
    progress_str = f"[{question_num}/{total_questions}]" if question_num and total_questions else ""
    logger.info(f"\n{'='*70}")
    logger.info(f"[EVAL] {progress_str} Evaluating Question: {question_id}")
    logger.info(f"{'='*70}")
    logger.info(f"[EVAL] Category: {question.get('category', 'N/A')}")
    logger.info(f"[EVAL] Ground Truth: {question['ground_truth_percentage']}%")
    
    ground_truth = question["ground_truth"]
    result = {
        "question_id": question_id,
        "question_text": question["question_text"],
        "ground_truth": ground_truth,
        "ground_truth_percentage": question["ground_truth_percentage"],
    }
    
    # Run orchestrated forecast
    logger.info("[EVAL] Running orchestrated multi-agent forecast...")
    try:
        forecast_result = await run_forecast(
            question_text=question["question_text"],
            question_type=question["question_type"],
            agent_counts=agent_counts
        )
        
        # Extract predicted probability
        predicted_prob = forecast_result.get("prediction_probability")
        if predicted_prob is None:
            predicted_prob = forecast_result.get("confidence", 0.5)
            if forecast_result["prediction"] and forecast_result["prediction"].lower() == "no":
                predicted_prob = 1.0 - predicted_prob
        
        # Calculate metrics
        brier_score = calculate_brier_score(predicted_prob, ground_truth >= 0.5)
        calibration_error = calculate_calibration_error(predicted_prob, ground_truth)
        predicted_direction = "Yes" if predicted_prob >= 0.5 else "No"
        ground_truth_direction = "Yes" if ground_truth >= 0.5 else "No"
        direction_correct = predicted_direction == ground_truth_direction
        
        result["orchestrated"] = {
            "predicted_prob": predicted_prob,
            "predicted_percentage": round(predicted_prob * 100, 1),
            "prediction": forecast_result["prediction"],
            "prediction_probability": forecast_result.get("prediction_probability"),
            "confidence": forecast_result.get("confidence"),
            "brier_score": round(brier_score, 4),
            "calibration_error": round(calibration_error, 4),
            "direction_correct": direction_correct,
            "session_id": forecast_result["session_id"],
            "total_duration_seconds": forecast_result.get("total_duration_seconds"),
            "total_cost_tokens": forecast_result.get("total_cost_tokens", 0),
            "status": forecast_result["status"]
        }
    except Exception as e:
        logger.error(f"[EVAL] Orchestrated forecast failed: {e}", exc_info=True)
        result["orchestrated"] = {
            "status": "failed",
            "error": str(e)
        }
    
    # Run one-shot baseline
    if run_baseline:
        logger.info("[EVAL] Running one-shot baseline...")
        try:
            baseline_result = await run_one_shot_baseline(
                question_text=question["question_text"],
                question_type=question["question_type"]
            )
            
            if baseline_result["status"] == "completed":
                baseline_predicted_prob = baseline_result.get("prediction_probability")
                if baseline_predicted_prob is None:
                    baseline_predicted_prob = baseline_result.get("confidence", 0.5)
                    if baseline_result["prediction"] and baseline_result["prediction"].lower() == "no":
                        baseline_predicted_prob = 1.0 - baseline_predicted_prob
                
                baseline_brier = calculate_brier_score(baseline_predicted_prob, ground_truth >= 0.5)
                baseline_calibration_error = calculate_calibration_error(baseline_predicted_prob, ground_truth)
                baseline_direction = "Yes" if baseline_predicted_prob >= 0.5 else "No"
                baseline_direction_correct = baseline_direction == ground_truth_direction
                
                result["baseline"] = {
                    "predicted_prob": baseline_predicted_prob,
                    "predicted_percentage": round(baseline_predicted_prob * 100, 1),
                    "prediction": baseline_result["prediction"],
                    "prediction_probability": baseline_result.get("prediction_probability"),
                    "confidence": baseline_result.get("confidence"),
                    "brier_score": round(baseline_brier, 4),
                    "calibration_error": round(baseline_calibration_error, 4),
                    "direction_correct": baseline_direction_correct,
                    "total_duration_seconds": baseline_result.get("total_duration_seconds"),
                    "total_cost_tokens": baseline_result.get("total_cost_tokens", 0),
                    "status": baseline_result["status"]
                }
            else:
                result["baseline"] = {
                    "status": "failed",
                    "error": baseline_result.get("error", "Unknown error")
                }
        except Exception as e:
            logger.error(f"[EVAL] Baseline forecast failed: {e}", exc_info=True)
            result["baseline"] = {
                "status": "failed",
                "error": str(e)
            }
    
    eval_end = datetime.now()
    eval_duration = (eval_end - eval_start).total_seconds()
    result["eval_duration_seconds"] = round(eval_duration, 2)
    
    # Log results
    logger.info(f"\n[EVAL] {'='*70}")
    logger.info(f"[EVAL] ✓ Question {question_id} - EVALUATION COMPLETE")
    logger.info(f"[EVAL] {'='*70}")
    
    # Log orchestrated results
    if "orchestrated" in result and result["orchestrated"].get("status") == "completed":
        orch = result["orchestrated"]
        logger.info("[EVAL] ORCHESTRATED (Multi-Agent):")
        logger.info(f"[EVAL]   ┌─ Prediction: {orch.get('prediction', 'N/A')}")
        logger.info(f"[EVAL]   ├─ Predicted Probability: {orch['predicted_percentage']}%")
        logger.info(f"[EVAL]   ├─ Confidence: {orch.get('confidence', 0):.1%}")
        logger.info(f"[EVAL]   ├─ Ground Truth: {question['ground_truth_percentage']}%")
        logger.info(f"[EVAL]   ├─ Direction Match: {'✓ YES' if orch.get('direction_correct') else '✗ NO'}")
        logger.info(f"[EVAL]   ├─ Calibration Error: {orch['calibration_error']:.4f} ({orch['calibration_error']*100:.2f}%)")
        logger.info(f"[EVAL]   ├─ Brier Score: {orch['brier_score']:.4f}")
        logger.info(f"[EVAL]   ├─ Duration: {orch.get('total_duration_seconds', 0):.2f}s")
        logger.info(f"[EVAL]   └─ Tokens: {orch.get('total_cost_tokens', 0):,}")
    elif "orchestrated" in result:
        logger.info("[EVAL] ORCHESTRATED: ✗ FAILED")
        logger.info(f"[EVAL]   Error: {result['orchestrated'].get('error', 'Unknown')}")
    
    # Log baseline results
    if "baseline" in result and result["baseline"].get("status") == "completed":
        base = result["baseline"]
        logger.info("[EVAL] BASELINE (One-Shot Grok):")
        logger.info(f"[EVAL]   ┌─ Prediction: {base.get('prediction', 'N/A')}")
        logger.info(f"[EVAL]   ├─ Predicted Probability: {base['predicted_percentage']}%")
        logger.info(f"[EVAL]   ├─ Confidence: {base.get('confidence', 0):.1%}")
        logger.info(f"[EVAL]   ├─ Ground Truth: {question['ground_truth_percentage']}%")
        logger.info(f"[EVAL]   ├─ Direction Match: {'✓ YES' if base.get('direction_correct') else '✗ NO'}")
        logger.info(f"[EVAL]   ├─ Calibration Error: {base['calibration_error']:.4f} ({base['calibration_error']*100:.2f}%)")
        logger.info(f"[EVAL]   ├─ Brier Score: {base['brier_score']:.4f}")
        logger.info(f"[EVAL]   ├─ Duration: {base.get('total_duration_seconds', 0):.2f}s")
        logger.info(f"[EVAL]   └─ Tokens: {base.get('total_cost_tokens', 0):,}")
    elif "baseline" in result:
        logger.info("[EVAL] BASELINE: ✗ FAILED")
        logger.info(f"[EVAL]   Error: {result['baseline'].get('error', 'Unknown')}")
    
    logger.info(f"[EVAL] Total Eval Duration: {eval_duration:.2f}s")
    
    return result


async def evaluate_all(
    eval_set: Dict[str, Any],
    agent_counts: Dict[str, int] = None,
    max_concurrent: int = None,
    num_questions: int = None,
    run_baseline: bool = True
) -> List[Dict[str, Any]]:
    """
    Run forecasts for all questions in the eval set in parallel.
    
    Args:
        eval_set: The evaluation set dictionary
        agent_counts: Agent count configuration
        max_concurrent: Maximum number of concurrent forecasts (None = unlimited)
        num_questions: Number of questions to test (None = all questions)
    """
    questions = eval_set["questions"]
    
    # Limit number of questions if specified
    if num_questions is not None and num_questions > 0:
        questions = questions[:num_questions]
        total_in_set = len(eval_set['questions'])
        logger.info(f"[EVAL] Limiting to first {num_questions} questions (out of {total_in_set} total)")
    
    total_questions = len(questions)
    
    logger.info(f"\n[EVAL] {'='*70}")
    logger.info("[EVAL] EVALUATION RUN CONFIGURATION")
    logger.info(f"[EVAL] {'='*70}")
    logger.info(f"[EVAL] Total Questions: {total_questions}")
    logger.info(f"[EVAL] Execution Mode: {'Parallel (unlimited)' if not max_concurrent else f'Parallel (max {max_concurrent} concurrent)'}")
    logger.info("[EVAL] Agent Configuration:")
    logger.info(f"[EVAL]   Phase 1 (Discovery): {agent_counts.get('phase_1_discovery', 'N/A')}")
    logger.info(f"[EVAL]   Phase 2 (Validation): {agent_counts.get('phase_2_validation', 'N/A')}")
    logger.info(f"[EVAL]   Phase 3 (Research): {agent_counts.get('phase_3_research', 'N/A')}")
    logger.info(f"[EVAL]   Phase 4 (Synthesis): {agent_counts.get('phase_4_synthesis', 'N/A')}")
    logger.info(f"[EVAL] {'='*70}\n")
    
    # Create tasks for all questions
    tasks = [
        evaluate_question(
            question,
            agent_counts=agent_counts,
            question_num=i+1,
            total_questions=total_questions,
            run_baseline=run_baseline
        )
        for i, question in enumerate(questions)
    ]
    
    # Run with optional concurrency limit
    if max_concurrent and max_concurrent < total_questions:
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        logger.info(f"[EVAL] Starting {total_questions} forecasts with max {max_concurrent} concurrent...")
        results = await asyncio.gather(*[bounded_task(task) for task in tasks], return_exceptions=True)
    else:
        logger.info(f"[EVAL] Starting {total_questions} forecasts in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions that weren't caught
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"[EVAL] ✗ Unhandled exception for question {questions[i]['id']}: {result}", exc_info=True)
            processed_results.append({
                "question_id": questions[i]["id"],
                "question_text": questions[i]["question_text"],
                "error": str(result),
                "status": "failed"
            })
        else:
            processed_results.append(result)
    
    logger.info(f"\n[EVAL] {'='*70}")
    logger.info("[EVAL] All forecasts completed")
    logger.info(f"[EVAL] {'='*70}\n")
    
    return processed_results


def calculate_summary_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics for the evaluation results (orchestrated + baseline)"""
    def calc_stats_for_method(method_key: str) -> Dict[str, Any]:
        """Calculate stats for a specific method (orchestrated or baseline)"""
        method_results = [r for r in results if method_key in r and r[method_key].get("status") == "completed"]
        
        if not method_results:
            return {"status": "no_data"}
        
        brier_scores = [r[method_key]["brier_score"] for r in method_results]
        calibration_errors = [r[method_key]["calibration_error"] for r in method_results]
        durations = [r[method_key].get("total_duration_seconds", 0) for r in method_results]
        tokens = [r[method_key].get("total_cost_tokens", 0) for r in method_results]
        
        # Calculate direction accuracy
        direction_matches = [r[method_key].get("direction_correct", False) for r in method_results]
        direction_accuracy = sum(direction_matches) / len(direction_matches) if direction_matches else 0
        
        return {
            "successful_forecasts": len(method_results),
            "mean_brier_score": round(sum(brier_scores) / len(brier_scores), 4),
            "std_brier_score": round((sum((x - sum(brier_scores)/len(brier_scores))**2 for x in brier_scores) / len(brier_scores))**0.5, 4) if len(brier_scores) > 1 else 0,
            "mean_calibration_error": round(sum(calibration_errors) / len(calibration_errors), 4),
            "max_calibration_error": round(max(calibration_errors), 4),
            "min_calibration_error": round(min(calibration_errors), 4),
            "std_calibration_error": round((sum((x - sum(calibration_errors)/len(calibration_errors))**2 for x in calibration_errors) / len(calibration_errors))**0.5, 4) if len(calibration_errors) > 1 else 0,
            "direction_accuracy": round(direction_accuracy, 4),
            "total_tokens": sum(tokens),
            "mean_tokens": round(sum(tokens) / len(tokens), 0) if tokens else 0,
            "mean_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
            "min_duration_seconds": round(min(durations), 2) if durations else 0,
            "max_duration_seconds": round(max(durations), 2) if durations else 0,
        }
    
    failed_results = [r for r in results if "orchestrated" not in r or r.get("orchestrated", {}).get("status") != "completed"]
    
    summary = {
        "total_questions": len(results),
        "failed_forecasts": len(failed_results),
        "orchestrated": calc_stats_for_method("orchestrated"),
        "baseline": calc_stats_for_method("baseline"),
    }
    
    # Add comparison metrics if both methods have data
    if summary["orchestrated"].get("status") != "no_data" and summary["baseline"].get("status") != "no_data":
        orch_mean_error = summary["orchestrated"]["mean_calibration_error"]
        base_mean_error = summary["baseline"]["mean_calibration_error"]
        summary["comparison"] = {
            "calibration_error_improvement": round(base_mean_error - orch_mean_error, 4),
            "calibration_error_improvement_pct": round((base_mean_error - orch_mean_error) / base_mean_error * 100, 2) if base_mean_error > 0 else 0,
            "brier_score_improvement": round(summary["baseline"]["mean_brier_score"] - summary["orchestrated"]["mean_brier_score"], 4),
            "speed_ratio": round(summary["baseline"]["mean_duration_seconds"] / summary["orchestrated"]["mean_duration_seconds"], 2) if summary["orchestrated"]["mean_duration_seconds"] > 0 else 0,
            "token_ratio": round(summary["orchestrated"]["total_tokens"] / summary["baseline"]["total_tokens"], 2) if summary["baseline"]["total_tokens"] > 0 else 0,
        }
    
    return summary


async def main():
    """Main evaluation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run evaluation on Kalshi eval set")
    parser.add_argument(
        "--eval-file",
        type=str,
        default="kalshi_eval_set.json",
        help="Path to eval set JSON file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="eval_results.json",
        help="Path to output results JSON file"
    )
    parser.add_argument(
        "--phase-1-count",
        type=int,
        default=5,
        help="Number of Phase 1 (Discovery) agents"
    )
    parser.add_argument(
        "--phase-2-count",
        type=int,
        default=2,
        help="Number of Phase 2 (Validation) agents (default: 2 - validator + rating_consensus)"
    )
    parser.add_argument(
        "--phase-3-count",
        type=int,
        default=5,
        help="Number of Phase 3 (Research) agents"
    )
    parser.add_argument(
        "--phase-4-count",
        type=int,
        default=1,
        help="Number of Phase 4 (Synthesis) agents (default: 1 - always 1)"
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        default=None,
        help="Number of questions from eval set to test (default: all questions)"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=None,
        help="Maximum number of concurrent forecasts (default: unlimited)"
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip one-shot baseline comparison (default: run baseline)"
    )
    
    args = parser.parse_args()
    
    # Load eval set
    eval_set = load_eval_set(args.eval_file)
    logger.info(f"[EVAL] Loaded eval set: {eval_set['name']}")
    logger.info(f"[EVAL] Total questions: {eval_set['metadata']['total_questions']}")
    
    # Configure agent counts
    agent_counts = {
        "phase_1_discovery": args.phase_1_count,
        "phase_2_validation": args.phase_2_count,
        "phase_3_research": args.phase_3_count,
        "phase_4_synthesis": args.phase_4_count
    }
    logger.info(f"[EVAL] Agent counts: {agent_counts}")
    
    # Warn if phase 2 or 4 counts are non-standard
    if args.phase_2_count != 2:
        logger.warning(f"[EVAL] Warning: Phase 2 count is {args.phase_2_count} (standard is 2: validator + rating_consensus)")
    if args.phase_4_count != 1:
        logger.warning(f"[EVAL] Warning: Phase 4 count is {args.phase_4_count} (standard is 1: synthesizer)")
    
    # Run evaluations
    logger.info(f"\n{'='*60}")
    logger.info("[EVAL] Starting evaluation run")
    logger.info(f"{'='*60}\n")
    
    run_baseline = not args.no_baseline
    if run_baseline:
        logger.info("[EVAL] Baseline comparison: ENABLED (one-shot Grok)")
    else:
        logger.info("[EVAL] Baseline comparison: DISABLED")
    
    start_time = datetime.now()
    results = await evaluate_all(
        eval_set,
        agent_counts=agent_counts,
        max_concurrent=args.max_concurrent,
        num_questions=args.num_questions,
        run_baseline=run_baseline
    )
    end_time = datetime.now()
    
    # Calculate summary statistics
    summary = calculate_summary_stats(results)
    
    # Build filename with parameters
    filename_parts = ["eval_results"]
    if args.num_questions:
        filename_parts.append(f"n{args.num_questions}")
    filename_parts.append(f"p1-{args.phase_1_count}")
    filename_parts.append(f"p2-{args.phase_2_count}")
    filename_parts.append(f"p3-{args.phase_3_count}")
    filename_parts.append(f"p4-{args.phase_4_count}")
    if args.max_concurrent:
        filename_parts.append(f"max{args.max_concurrent}")
    
    # Extract base filename and extension from args.output
    if args.output.endswith(".json"):
        base_name = args.output[:-5]  # Remove .json extension
    else:
        base_name = args.output
    
    filename = f"{base_name}_{'_'.join(filename_parts)}.json"
    
    # Check if file exists and append timestamp if it does
    output_path = Path(__file__).parent / filename
    if output_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = filename[:-5]  # Remove .json extension
        filename = f"{base_filename}_{timestamp}.json"
        output_path = Path(__file__).parent / filename
        logger.info(f"[EVAL] File already exists, appending timestamp: {filename}")
    
    # Prepare output with parameters at the top
    output = {
        "eval_parameters": {
            "eval_set": eval_set["name"],
            "eval_file": args.eval_file,
            "num_questions": args.num_questions if args.num_questions else len(eval_set["questions"]),
            "total_questions_in_set": len(eval_set["questions"]),
            "agent_counts": agent_counts,
            "max_concurrent": args.max_concurrent,
            "eval_date": datetime.now().isoformat()
        },
        "summary": summary,
        "results": results,
        "total_eval_duration_seconds": round((end_time - start_time).total_seconds(), 2)
    }
    
    # Save results
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    total_eval_duration = (end_time - start_time).total_seconds()
    
    logger.info(f"\n{'='*70}")
    logger.info("[EVAL] EVALUATION COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"[EVAL] Total Evaluation Duration: {total_eval_duration:.2f}s ({total_eval_duration/60:.2f} minutes)")
    logger.info(f"[EVAL] Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"\n[EVAL] {'='*70}")
    logger.info("[EVAL] SUMMARY STATISTICS")
    logger.info(f"[EVAL] {'='*70}")
    logger.info(f"[EVAL] Total Questions: {summary.get('total_questions', 0)}")
    logger.info(f"[EVAL] Failed Forecasts: {summary.get('failed_forecasts', 0)}")
    logger.info("")
    
    # Orchestrated stats
    orch = summary.get("orchestrated", {})
    if orch.get("status") != "no_data":
        logger.info("[EVAL] ORCHESTRATED (Multi-Agent System):")
        logger.info(f"[EVAL]   ┌─ Successful: {orch.get('successful_forecasts', 0)}")
        logger.info(f"[EVAL]   ├─ Direction Accuracy: {orch.get('direction_accuracy', 0)*100:.1f}%")
        logger.info(f"[EVAL]   ├─ Mean Brier Score: {orch.get('mean_brier_score', 'N/A')} (std: {orch.get('std_brier_score', 'N/A')})")
        logger.info(f"[EVAL]   ├─ Mean Calibration Error: {orch.get('mean_calibration_error', 'N/A')} ({orch.get('mean_calibration_error', 0)*100:.2f}%)")
        logger.info(f"[EVAL]   ├─ Mean Duration: {orch.get('mean_duration_seconds', 0):.2f}s")
        logger.info(f"[EVAL]   └─ Total Tokens: {orch.get('total_tokens', 0):,} (mean: {orch.get('mean_tokens', 0):,.0f})")
    else:
        logger.info("[EVAL] ORCHESTRATED: No data")
    
    logger.info("")
    
    # Baseline stats
    base = summary.get("baseline", {})
    if base.get("status") != "no_data":
        logger.info("[EVAL] BASELINE (One-Shot Grok):")
        logger.info(f"[EVAL]   ┌─ Successful: {base.get('successful_forecasts', 0)}")
        logger.info(f"[EVAL]   ├─ Direction Accuracy: {base.get('direction_accuracy', 0)*100:.1f}%")
        logger.info(f"[EVAL]   ├─ Mean Brier Score: {base.get('mean_brier_score', 'N/A')} (std: {base.get('std_brier_score', 'N/A')})")
        logger.info(f"[EVAL]   ├─ Mean Calibration Error: {base.get('mean_calibration_error', 'N/A')} ({base.get('mean_calibration_error', 0)*100:.2f}%)")
        logger.info(f"[EVAL]   ├─ Mean Duration: {base.get('mean_duration_seconds', 0):.2f}s")
        logger.info(f"[EVAL]   └─ Total Tokens: {base.get('total_tokens', 0):,} (mean: {base.get('mean_tokens', 0):,.0f})")
    else:
        logger.info("[EVAL] BASELINE: No data")
    
    # Comparison
    comp = summary.get("comparison")
    if comp:
        logger.info("")
        logger.info("[EVAL] COMPARISON (Orchestrated vs Baseline):")
        logger.info(f"[EVAL]   ┌─ Calibration Error Improvement: {comp.get('calibration_error_improvement', 0):.4f} ({comp.get('calibration_error_improvement_pct', 0):.2f}% better)")
        logger.info(f"[EVAL]   ├─ Brier Score Improvement: {comp.get('brier_score_improvement', 0):.4f}")
        logger.info(f"[EVAL]   ├─ Speed Ratio: {comp.get('speed_ratio', 0):.2f}x (baseline is faster)")
        logger.info(f"[EVAL]   └─ Token Ratio: {comp.get('token_ratio', 0):.2f}x (orchestrated uses more tokens)")
    logger.info(f"\n[EVAL] {'='*70}")
    logger.info(f"[EVAL] Results saved to: {output_path}")
    logger.info(f"[EVAL] Filename includes parameters: {filename}")
    logger.info(f"[EVAL] {'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())

