"""
Main evaluation script - orchestrates the model evaluation framework.
"""

import argparse
import sys
from typing import List, Optional
from prompt_loader import PromptLoader
from model_evaluator import ModelEvaluator
from results_aggregator import ResultsAggregator
from config import MODELS, PROMPT_SETTINGS, AWS_REGION


def main():
    """Main entry point for evaluation framework."""
    parser = argparse.ArgumentParser(
        description="Evaluate LLM models on Bedrock",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate all configured models with local CSV file
  python evaluate.py --prompts prompts.csv --models claude-sonnet llama-3-2-11b
  
  # Evaluate from S3
  python evaluate.py --s3-bucket my-bucket --s3-key prompts.csv --models claude-sonnet
  
  # Limit to 10 prompts
  python evaluate.py --prompts prompts.csv --max-prompts 10
  
  # Custom output directory
  python evaluate.py --prompts prompts.csv --output-dir ./eval_results
        """
    )
    
    # Prompt source options
    prompt_group = parser.add_mutually_exclusive_group(required=False)
    prompt_group.add_argument("--prompts", type=str, help="Local path to prompts file (.csv, .json, or .txt)")
    prompt_group.add_argument("--s3-bucket", type=str, help="S3 bucket name for prompts")
    prompt_group.add_argument("--s3-key", type=str, help="S3 key/path for prompts file")
    
    # Model selection
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        default=list(MODELS.keys()),
        choices=list(MODELS.keys()),
        help=f"Models to evaluate (default: all). Available: {', '.join(MODELS.keys())}"
    )
    
    # Evaluation options
    parser.add_argument("--max-prompts", type=int, help="Maximum number of prompts to evaluate")
    parser.add_argument("--output-dir", type=str, default="results", help="Output directory for results (default: results)")
    parser.add_argument("--skip-summary", action="store_true", help="Skip printing summary table")
    
    args = parser.parse_args()
    
    # Update config based on CLI arguments
    if args.prompts:
        PROMPT_SETTINGS["local_path"] = args.prompts
    if args.s3_bucket:
        PROMPT_SETTINGS["s3_bucket"] = args.s3_bucket
    if args.s3_key:
        PROMPT_SETTINGS["s3_key"] = args.s3_key
    
    # Validate models
    invalid_models = [m for m in args.models if m not in MODELS]
    if invalid_models:
        print(f"Error: Invalid model keys: {invalid_models}")
        print(f"Available models: {', '.join(MODELS.keys())}")
        sys.exit(1)
    
    # Load prompts
    print("Loading prompts...")
    try:
        loader = PromptLoader(source_type="auto")
        prompts = loader.load_prompts(max_prompts=args.max_prompts)
        
        if not prompts:
            print("Error: No prompts loaded")
            sys.exit(1)
        
        print(f"Loaded {len(prompts)} prompts")
    except Exception as e:
        print(f"Error loading prompts: {e}")
        sys.exit(1)
    
    # Evaluate each model
    all_results = []
    summaries = []
    
    for model_key in args.models:
        try:
            evaluator = ModelEvaluator(model_key)
            results = evaluator.evaluate_prompts(prompts)
            summary = evaluator.get_summary_stats()
            
            all_results.extend(results)
            summaries.append(summary)
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ Error evaluating {model_key}: {error_msg}")
            
            # Special handling for Anthropic access errors
            if "use case details" in error_msg.lower() or "ResourceNotFoundException" in error_msg:
                print(f"\n⚠️  IMPORTANT: Anthropic model access not enabled!")
                print(f"   To fix this, enable Anthropic models in AWS Bedrock:")
                print(f"   https://console.aws.amazon.com/bedrock/home?region={AWS_REGION}#/modelaccess")
                print(f"   See MANUAL_GUIDE.md section 'Issue 3.5' for step-by-step instructions.\n")
            
            continue
    
    if not all_results:
        print("Error: No results collected")
        sys.exit(1)
    
    # Check for Anthropic access errors in results
    anthropic_errors = []
    for result in all_results:
        if result.get("output", "").startswith("❌") and "use case details" in result.get("output", "").lower():
            model_name = result.get("model_name", "Unknown")
            if model_name not in [e["model"] for e in anthropic_errors]:
                anthropic_errors.append({"model": model_name, "count": 1})
            else:
                for e in anthropic_errors:
                    if e["model"] == model_name:
                        e["count"] += 1
                        break
    
    # Generate reports
    print("\nGenerating reports...")
    aggregator = ResultsAggregator(output_dir=args.output_dir)
    
    detailed_file = aggregator.save_detailed_results(all_results)
    summary_file = aggregator.save_summary_report(summaries)
    comparison_file = aggregator.save_comparison_report(all_results, summaries)
    
    # Print summary
    if not args.skip_summary:
        aggregator.print_summary_table(summaries)
    
    print(f"\n✓ Evaluation complete!")
    print(f"  Detailed results: {detailed_file}")
    print(f"  Summary report: {summary_file}")
    print(f"  Comparison report: {comparison_file}")
    
    # Show Anthropic access error summary if any
    if anthropic_errors:
        print(f"\n{'='*80}")
        print(f"⚠️  ANTHROPIC MODEL ACCESS ERROR DETECTED")
        print(f"{'='*80}")
        for error_info in anthropic_errors:
            print(f"\n❌ {error_info['model']}: {error_info['count']} error(s) due to missing Anthropic access")
        print(f"\n🔧 TO FIX THIS:")
        print(f"   1. Go to: https://console.aws.amazon.com/bedrock/home?region={AWS_REGION}#/modelaccess")
        print(f"   2. Find 'Anthropic' and click 'Request model access' or 'Enable'")
        print(f"   3. Fill out the use case form and submit")
        print(f"   4. Wait 5-15 minutes for approval")
        print(f"   5. Re-run your evaluation")
        print(f"\n📖 See FIX_ANTHROPIC_ACCESS.md for detailed step-by-step instructions")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

