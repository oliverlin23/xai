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
    
    return {
        "session_id": session_id,
        "prediction": prediction_result.get("prediction"),
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
    total_questions: int = None
) -> Dict[str, Any]:
    """Evaluate a single question and return results"""
    question_id = question["id"]
    eval_start = datetime.now()
    
    progress_str = f"[{question_num}/{total_questions}]" if question_num and total_questions else ""
    logger.info(f"\n{'='*70}")
    logger.info(f"[EVAL] {progress_str} Evaluating Question: {question_id}")
    logger.info(f"{'='*70}")
    logger.info(f"[EVAL] Category: {question.get('category', 'N/A')}")
    logger.info(f"[EVAL] Ground Truth: {question['ground_truth_percentage']}%")
    
    try:
        forecast_result = await run_forecast(
            question_text=question["question_text"],
            question_type=question["question_type"],
            agent_counts=agent_counts
        )
        
        eval_end = datetime.now()
        eval_duration = (eval_end - eval_start).total_seconds()
        
        # Extract predicted probability
        # Use prediction_probability if available, otherwise fall back to confidence for backward compatibility
        predicted_prob = forecast_result.get("prediction_probability")
        if predicted_prob is None:
            # Fallback: use confidence as probability (backward compatibility)
            predicted_prob = forecast_result.get("confidence", 0.5)
            if forecast_result["prediction"] and forecast_result["prediction"].lower() == "no":
                predicted_prob = 1.0 - predicted_prob
        
        ground_truth = question["ground_truth"]
        
        # Calculate metrics
        brier_score = calculate_brier_score(predicted_prob, ground_truth >= 0.5)
        calibration_error = calculate_calibration_error(predicted_prob, ground_truth)
        
        # Determine if prediction direction matches ground truth
        predicted_direction = "Yes" if predicted_prob >= 0.5 else "No"
        ground_truth_direction = "Yes" if ground_truth >= 0.5 else "No"
        direction_correct = predicted_direction == ground_truth_direction
        
        result = {
            "question_id": question_id,
            "question_text": question["question_text"],
            "ground_truth": ground_truth,
            "ground_truth_percentage": question["ground_truth_percentage"],
            "predicted_prob": predicted_prob,
            "predicted_percentage": round(predicted_prob * 100, 1),
            "prediction": forecast_result["prediction"],
            "prediction_probability": forecast_result.get("prediction_probability"),
            "confidence": forecast_result.get("confidence"),  # Confidence in the probability estimate
            "brier_score": round(brier_score, 4),
            "calibration_error": round(calibration_error, 4),
            "session_id": forecast_result["session_id"],
            "total_duration_seconds": forecast_result.get("total_duration_seconds"),
            "total_cost_tokens": forecast_result.get("total_cost_tokens", 0),
            "status": forecast_result["status"],
            "eval_duration_seconds": round(eval_duration, 2)
        }
        
        logger.info(f"\n[EVAL] {'='*70}")
        logger.info(f"[EVAL] ✓ Question {question_id} - EVALUATION COMPLETE")
        logger.info(f"[EVAL] {'='*70}")
        logger.info("[EVAL] Results:")
        logger.info(f"[EVAL]   ┌─ Prediction: {forecast_result.get('prediction', 'N/A')}")
        logger.info(f"[EVAL]   ├─ Confidence: {forecast_result.get('confidence', 0):.1%}")
        logger.info(f"[EVAL]   ├─ Predicted Probability: {result['predicted_percentage']}%")
        logger.info(f"[EVAL]   ├─ Ground Truth: {question['ground_truth_percentage']}%")
        logger.info(f"[EVAL]   ├─ Direction Match: {'✓ YES' if direction_correct else '✗ NO'}")
        logger.info(f"[EVAL]   ├─ Calibration Error: {result['calibration_error']:.4f} ({result['calibration_error']*100:.2f}%)")
        logger.info(f"[EVAL]   ├─ Brier Score: {result['brier_score']:.4f}")
        logger.info(f"[EVAL]   ├─ Duration: {result.get('total_duration_seconds', 0):.2f}s")
        logger.info(f"[EVAL]   ├─ Tokens: {result.get('total_cost_tokens', 0):,}")
        logger.info(f"[EVAL]   └─ Session ID: {forecast_result['session_id']}")
        if forecast_result.get("key_factors"):
            logger.info(f"[EVAL] Key Factors ({len(forecast_result.get('key_factors', []))}):")
            for i, factor in enumerate(forecast_result.get("key_factors", [])[:5], 1):
                logger.info(f"[EVAL]   {i}. {factor}")
        
        return result
        
    except Exception as e:
        eval_end = datetime.now()
        eval_duration = (eval_end - eval_start).total_seconds()
        logger.error(f"\n[EVAL] {'='*70}")
        logger.error(f"[EVAL] ✗ Question {question_id} - FAILED")
        logger.error(f"[EVAL] {'='*70}")
        logger.error(f"[EVAL] Error: {str(e)}")
        logger.error(f"[EVAL] Duration before failure: {eval_duration:.2f}s")
        logger.error("[EVAL] Exception details:", exc_info=True)
        return {
            "question_id": question_id,
            "question_text": question["question_text"],
            "error": str(e),
            "status": "failed",
            "eval_duration_seconds": round(eval_duration, 2)
        }


async def evaluate_all(
    eval_set: Dict[str, Any],
    agent_counts: Dict[str, int] = None,
    max_concurrent: int = None,
    num_questions: int = None
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
            total_questions=total_questions
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
    """Calculate summary statistics for the evaluation results"""
    successful_results = [r for r in results if "brier_score" in r]
    failed_results = [r for r in results if r.get("status") == "failed"]
    
    if not successful_results:
        return {"error": "No successful forecasts"}
    
    brier_scores = [r["brier_score"] for r in successful_results]
    calibration_errors = [r["calibration_error"] for r in successful_results]
    durations = [r.get("total_duration_seconds", 0) for r in successful_results]
    tokens = [r.get("total_cost_tokens", 0) for r in successful_results]
    
    # Calculate direction accuracy (how many predictions matched ground truth direction)
    direction_matches = []
    for r in successful_results:
        predicted_direction = "Yes" if r["predicted_prob"] >= 0.5 else "No"
        ground_truth_direction = "Yes" if r["ground_truth"] >= 0.5 else "No"
        direction_matches.append(predicted_direction == ground_truth_direction)
    
    direction_accuracy = sum(direction_matches) / len(direction_matches) if direction_matches else 0
    
    return {
        "total_questions": len(results),
        "successful_forecasts": len(successful_results),
        "failed_forecasts": len(failed_results),
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
    
    start_time = datetime.now()
    results = await evaluate_all(
        eval_set,
        agent_counts=agent_counts,
        max_concurrent=args.max_concurrent,
        num_questions=args.num_questions
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
    output_path = Path(__file__).parent / filename
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
    logger.info("[EVAL] Success Rate:")
    logger.info(f"[EVAL]   ┌─ Successful: {summary.get('successful_forecasts', 0)}/{summary.get('total_questions', 0)}")
    logger.info(f"[EVAL]   └─ Failed: {summary.get('failed_forecasts', 0)}/{summary.get('total_questions', 0)}")
    logger.info("[EVAL]")
    logger.info("[EVAL] Prediction Accuracy:")
    logger.info(f"[EVAL]   ┌─ Direction Accuracy: {summary.get('direction_accuracy', 0)*100:.1f}%")
    logger.info(f"[EVAL]   ├─ Mean Brier Score: {summary.get('mean_brier_score', 'N/A')} (std: {summary.get('std_brier_score', 'N/A')})")
    logger.info(f"[EVAL]   ├─ Mean Calibration Error: {summary.get('mean_calibration_error', 'N/A')} ({summary.get('mean_calibration_error', 0)*100:.2f}%)")
    logger.info(f"[EVAL]   ├─ Min Calibration Error: {summary.get('min_calibration_error', 'N/A')}")
    logger.info(f"[EVAL]   └─ Max Calibration Error: {summary.get('max_calibration_error', 'N/A')}")
    logger.info("[EVAL]")
    logger.info("[EVAL] Performance Metrics:")
    logger.info(f"[EVAL]   ┌─ Total Tokens: {summary.get('total_tokens', 0):,}")
    logger.info(f"[EVAL]   ├─ Mean Tokens per Forecast: {summary.get('mean_tokens', 0):,.0f}")
    logger.info(f"[EVAL]   ├─ Mean Duration: {summary.get('mean_duration_seconds', 0):.2f}s")
    logger.info(f"[EVAL]   ├─ Min Duration: {summary.get('min_duration_seconds', 0):.2f}s")
    logger.info(f"[EVAL]   └─ Max Duration: {summary.get('max_duration_seconds', 0):.2f}s")
    logger.info("[EVAL]")
    logger.info("[EVAL] Individual Results:")
    for i, result in enumerate(results, 1):
        if "brier_score" in result:
            status_icon = "✓" if result.get("status") == "completed" else "✗"
            logger.info(f"[EVAL]   {i}. {status_icon} {result['question_id']}: "
                       f"Predicted {result['predicted_percentage']}% "
                       f"(Ground Truth: {result['ground_truth_percentage']}%) "
                       f"| Error: {result['calibration_error']:.4f} "
                       f"| Brier: {result['brier_score']:.4f}")
        else:
            logger.info(f"[EVAL]   {i}. ✗ {result.get('question_id', 'Unknown')}: FAILED - {result.get('error', 'Unknown error')}")
    logger.info(f"\n[EVAL] {'='*70}")
    logger.info(f"[EVAL] Results saved to: {output_path}")
    logger.info(f"[EVAL] Filename includes parameters: {filename}")
    logger.info(f"[EVAL] {'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())

