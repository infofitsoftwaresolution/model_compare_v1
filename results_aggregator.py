"""
Results aggregator module - generates CSV reports and summary statistics.
"""

import csv
import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path


class ResultsAggregator:
    """Aggregates evaluation results and generates reports."""
    
    def __init__(self, output_dir: str = "results"):
        """
        Initialize results aggregator.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def save_detailed_results(self, all_results: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Save detailed results for all prompts and models to CSV.
        
        Args:
            all_results: List of result dictionaries from model evaluations
            filename: Optional custom filename (default: detailed_results_TIMESTAMP.csv)
            
        Returns:
            Path to saved file
        """
        if not all_results:
            raise ValueError("No results to save")
        
        if filename is None:
            filename = f"detailed_results_{self.timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        # Get all unique field names
        fieldnames = set()
        for result in all_results:
            fieldnames.update(result.keys())
        
        fieldnames = sorted(fieldnames)
        
        # Ensure key columns are first
        priority_fields = ["prompt_index", "model_key", "model_name", "input_tokens", 
                          "output_tokens", "latency_ms", "cost_usd", "valid_json", "retries"]
        ordered_fields = [f for f in priority_fields if f in fieldnames]
        ordered_fields.extend([f for f in fieldnames if f not in priority_fields])
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_results)
        
        print(f"\nDetailed results saved to: {filepath}")
        return str(filepath)
    
    def save_summary_report(self, summaries: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Save summary statistics comparing all models to CSV.
        
        Args:
            summaries: List of summary dictionaries from get_summary_stats()
            filename: Optional custom filename (default: summary_TIMESTAMP.csv)
            
        Returns:
            Path to saved file
        """
        if not summaries:
            raise ValueError("No summaries to save")
        
        if filename is None:
            filename = f"summary_{self.timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        # Define field order for summary
        fieldnames = [
            "model_key", "model_name", "total_prompts",
            "avg_latency_ms", "p50_latency_ms", "p95_latency_ms", 
            "min_latency_ms", "max_latency_ms",
            "total_cost_usd", "avg_cost_usd",
            "valid_json_rate", "valid_json_count",
            "total_input_tokens", "total_output_tokens",
            "avg_input_tokens", "avg_output_tokens",
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(summaries)
        
        print(f"Summary report saved to: {filepath}")
        return str(filepath)
    
    def print_summary_table(self, summaries: List[Dict[str, Any]]):
        """Print a formatted summary table to console."""
        if not summaries:
            return
        
        print("\n" + "="*100)
        print("EVALUATION SUMMARY")
        print("="*100)
        
        # Header
        header = f"{'Model':<25} {'Avg Lat (ms)':<15} {'P50 (ms)':<12} {'P95 (ms)':<12} "
        header += f"{'Avg Cost ($)':<15} {'JSON Valid %':<15} {'Total Cost ($)':<15}"
        print(header)
        print("-" * 100)
        
        # Rows
        for summary in summaries:
            model_name = summary.get("model_name", summary.get("model_key", "Unknown"))
            avg_lat = summary.get("avg_latency_ms", 0)
            p50 = summary.get("p50_latency_ms", 0)
            p95 = summary.get("p95_latency_ms", 0)
            avg_cost = summary.get("avg_cost_usd", 0)
            json_rate = summary.get("valid_json_rate", 0) * 100
            total_cost = summary.get("total_cost_usd", 0)
            
            row = f"{model_name:<25} {avg_lat:<15.2f} {p50:<12.2f} {p95:<12.2f} "
            row += f"{avg_cost:<15.6f} {json_rate:<14.2f}% {total_cost:<15.6f}"
            print(row)
        
        print("="*100)
        
        # Recommendations
        print("\nRECOMMENDATIONS:")
        
        # Best JSON validity
        best_json = max(summaries, key=lambda x: x.get("valid_json_rate", 0))
        print(f"  • Most Reliable (JSON): {best_json.get('model_name')} "
              f"({best_json.get('valid_json_rate', 0)*100:.1f}% valid)")
        
        # Lowest cost
        best_cost = min(summaries, key=lambda x: x.get("avg_cost_usd", float('inf')))
        print(f"  • Most Cost-Effective: {best_cost.get('model_name')} "
              f"(${best_cost.get('avg_cost_usd', 0):.6f} avg per prompt)")
        
        # Best latency
        best_latency = min(summaries, key=lambda x: x.get("p95_latency_ms", float('inf')))
        print(f"  • Best P95 Latency: {best_latency.get('model_name')} "
              f"({best_latency.get('p95_latency_ms', 0):.2f}ms)")
        
        # Best trade-off (low cost + good latency + high JSON validity)
        scored = []
        for s in summaries:
            cost_score = 1 / (s.get("avg_cost_usd", 0.0001) * 1000 + 1)  # Lower cost = higher score
            latency_score = 1 / (s.get("p95_latency_ms", 1) / 1000 + 1)  # Lower latency = higher score
            json_score = s.get("valid_json_rate", 0)  # Higher validity = higher score
            total_score = (cost_score * 0.3 + latency_score * 0.3 + json_score * 0.4)
            scored.append((s, total_score))
        
        if scored:
            best_overall = max(scored, key=lambda x: x[1])[0]
            print(f"  • Best Overall: {best_overall.get('model_name')} "
                  f"(balanced cost, latency, and reliability)")
        
        print()
    
    def save_comparison_report(self, all_results: List[Dict[str, Any]], summaries: List[Dict[str, Any]]) -> str:
        """
        Save a side-by-side comparison report.
        
        Args:
            all_results: Detailed results from all models
            summaries: Summary statistics
            
        Returns:
            Path to saved file
        """
        filename = f"comparison_{self.timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Group results by prompt index
        by_prompt = {}
        for result in all_results:
            idx = result.get("prompt_index")
            if idx not in by_prompt:
                by_prompt[idx] = {}
            model_key = result.get("model_key")
            by_prompt[idx][model_key] = result
        
        # Create comparison rows
        comparison_rows = []
        model_keys = sorted(set(r.get("model_key") for r in all_results))
        
        for prompt_idx in sorted(by_prompt.keys()):
            prompt_data = by_prompt[prompt_idx]
            first_model = prompt_data.get(model_keys[0], {})
            
            row = {
                "prompt_index": prompt_idx,
                "prompt_snippet": first_model.get("prompt_snippet", ""),
            }
            
            for model_key in model_keys:
                result = prompt_data.get(model_key, {})
                prefix = f"{model_key}_"
                row[f"{prefix}latency_ms"] = result.get("latency_ms")
                row[f"{prefix}cost_usd"] = result.get("cost_usd")
                row[f"{prefix}valid_json"] = result.get("valid_json")
                row[f"{prefix}input_tokens"] = result.get("input_tokens")
                row[f"{prefix}output_tokens"] = result.get("output_tokens")
            
            comparison_rows.append(row)
        
        # Write comparison CSV
        fieldnames = ["prompt_index", "prompt_snippet"]
        for model_key in model_keys:
            fieldnames.extend([
                f"{model_key}_latency_ms",
                f"{model_key}_cost_usd",
                f"{model_key}_valid_json",
                f"{model_key}_input_tokens",
                f"{model_key}_output_tokens",
            ])
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comparison_rows)
        
        print(f"Comparison report saved to: {filepath}")
        return str(filepath)

