"""Main script to run LLM evaluation on Bedrock models."""

import argparse
import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file if it exists
from pathlib import Path as PathLib
from dotenv import load_dotenv
env_path = PathLib(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

import pandas as pd
from tqdm import tqdm

from src.model_registry import ModelRegistry
from src.prompt_loader import load_prompts
from src.evaluator import BedrockEvaluator
from src.metrics_logger import MetricsLogger
from src.report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Run Bedrock LLM evaluation on test prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate all models on all prompts
  python scripts/run_evaluation.py --models all

  # Evaluate specific models
  python scripts/run_evaluation.py --models "Claude 3.7 Sonnet,Llama 3.2 11B Instruct"

  # Use custom prompts file
  python scripts/run_evaluation.py --prompts data/my_prompts.csv --out data/my_runs

  # Limit to first 10 prompts
  python scripts/run_evaluation.py --models all --limit 10
        """
    )
    
    parser.add_argument(
        "--models",
        default="all",
        help="Comma-separated model names or 'all' (default: all)"
    )
    parser.add_argument(
        "--prompts",
        default="data/test_prompts.csv",
        help="Path to prompts CSV file (default: data/test_prompts.csv)"
    )
    parser.add_argument(
        "--out",
        default="data/runs",
        help="Output directory for results (default: data/runs)"
    )
    parser.add_argument(
        "--config",
        default="configs/models.yaml",
        help="Path to models configuration YAML (default: configs/models.yaml)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of prompts to evaluate (useful for testing)"
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run ID for grouping results (default: auto-generated)"
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip generating aggregated report"
    )
    
    args = parser.parse_args()
    
    # Parse model names
    if args.models.lower() == "all":
        model_names = ["all"]
    else:
        model_names = [name.strip() for name in args.models.split(",")]
    
    # Validate paths
    prompts_path = Path(args.prompts)
    if not prompts_path.exists():
        print(f"❌ Error: Prompts file not found: {prompts_path}")
        sys.exit(1)
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Error: Config file not found: {config_path}")
        sys.exit(1)
    
    # Initialize components
    print("📋 Loading configuration...")
    model_registry = ModelRegistry(config_path)
    
    models = model_registry.get_models_by_names(model_names)
    if not models:
        print(f"❌ Error: No models found matching: {args.models}")
        print(f"   Available models: {[m['name'] for m in model_registry.list_models()]}")
        sys.exit(1)
    
    print(f"✅ Found {len(models)} model(s): {[m['name'] for m in models]}")
    
    print(f"📝 Loading prompts from {prompts_path}...")
    prompts_df = load_prompts(prompts_path)
    
    if args.limit:
        prompts_df = prompts_df.head(args.limit)
        print(f"   Limited to {len(prompts_df)} prompts")
    
    print(f"✅ Loaded {len(prompts_df)} prompt(s)")
    
    # Initialize evaluator
    print("🔧 Initializing evaluator...")
    evaluator = BedrockEvaluator(model_registry)
    
    # Initialize logger and reporter
    output_dir = Path(args.out)
    metrics_logger = MetricsLogger(output_dir)
    report_generator = ReportGenerator(output_dir)
    
    # Generate run ID
    run_id = args.run_id or f"run_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"🏃 Run ID: {run_id}")
    
    # Evaluate prompts
    print("\n🚀 Starting evaluation...")
    print(f"   Models: {len(models)}")
    print(f"   Prompts: {len(prompts_df)}")
    print(f"   Total evaluations: {len(models) * len(prompts_df)}")
    
    all_metrics = []
    total_evaluations = len(models) * len(prompts_df)
    
    try:
        with tqdm(total=total_evaluations, desc="Evaluating", unit="eval") as pbar:
            for _, prompt_row in prompts_df.iterrows():
                prompt_id = prompt_row.get("prompt_id")
                prompt = prompt_row.get("prompt", "")
                expected_json = bool(prompt_row.get("expected_json", False))
                
                if not prompt:
                    pbar.update(len(models))
                    continue
                
                for model in models:
                    try:
                        metrics = evaluator.evaluate_prompt(
                            prompt=prompt,
                            model=model,
                            prompt_id=prompt_id,
                            expected_json=expected_json,
                            run_id=run_id
                        )
                        all_metrics.append(metrics)
                        
                        # Update progress bar with status
                        status_emoji = "✅" if metrics["status"] == "success" else "❌"
                        pbar.set_postfix({
                            "model": model["name"][:20],
                            "status": status_emoji
                        })
                        
                    except Exception as e:
                        print(f"\n⚠️  Error evaluating {model['name']} on prompt {prompt_id}: {e}")
                        # Create error metric
                        error_metric = {
                            "timestamp": pd.Timestamp.now().isoformat() + "Z",
                            "run_id": run_id,
                            "model_name": model.get("name", "unknown"),
                            "model_id": model.get("bedrock_model_id", "unknown"),
                            "prompt_id": prompt_id,
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "latency_ms": 0,
                            "json_valid": False,
                            "error": str(e),
                            "status": "error",
                            "cost_usd_input": 0.0,
                            "cost_usd_output": 0.0,
                            "cost_usd_total": 0.0,
                        }
                        all_metrics.append(error_metric)
                    
                    pbar.update(1)
        
        print(f"\n✅ Evaluation complete! Collected {len(all_metrics)} metric records")
        
        # Log metrics
        print("💾 Saving metrics...")
        metrics_logger.log_metrics(all_metrics)
        print(f"   Saved to: {metrics_logger.raw_csv_path}")
        
        # Generate report
        if not args.skip_report:
            print("📊 Generating aggregated report...")
            comparison_df = report_generator.generate_report(raw_metrics_df=pd.DataFrame(all_metrics))
            
            if not comparison_df.empty:
                print(f"   Saved to: {report_generator.comparison_csv_path}")
                print("\n📈 Summary:")
                print(comparison_df.to_string(index=False))
            else:
                print("   ⚠️  No data to aggregate")
        
        print(f"\n✨ Done! Results saved to: {output_dir}")
        print(f"   - Raw metrics: {metrics_logger.raw_csv_path}")
        print(f"   - Comparison: {report_generator.comparison_csv_path}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation interrupted by user")
        if all_metrics:
            print(f"💾 Saving {len(all_metrics)} collected metrics...")
            metrics_logger.log_metrics(all_metrics)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
