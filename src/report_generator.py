"""Report generator: aggregates raw metrics into model-level summaries."""

from pathlib import Path
from typing import Optional, Union
import pandas as pd
import numpy as np


def percentile(series: pd.Series, p: float) -> float:
    """Calculate percentile, handling empty series."""
    if series.empty:
        return 0.0
    return float(series.quantile(p))


class ReportGenerator:
    """Generates aggregated reports from raw metrics."""
    
    def __init__(self, output_dir: Union[str, Path]):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.comparison_csv_path = self.output_dir / "model_comparison.csv"
    
    def generate_report(
        self,
        raw_metrics_df: Optional[pd.DataFrame] = None,
        raw_csv_path: Optional[Union[str, Path]] = None
    ) -> pd.DataFrame:
        """
        Generate aggregated comparison report.
        
        Args:
            raw_metrics_df: DataFrame with raw metrics (optional)
            raw_csv_path: Path to raw metrics CSV (optional)
        
        Returns:
            DataFrame with aggregated metrics per model
        """
        # Load data
        if raw_metrics_df is not None:
            df = raw_metrics_df.copy()
        elif raw_csv_path:
            csv_path = Path(raw_csv_path)
            if not csv_path.exists():
                return pd.DataFrame()
            try:
                df = pd.read_csv(
                    csv_path,
                    quoting=1,  # QUOTE_ALL
                    escapechar=None,
                    doublequote=True,
                    on_bad_lines='skip',  # Skip problematic lines
                    engine='python'
                )
            except Exception:
                try:
                    df = pd.read_csv(csv_path, on_bad_lines='skip', engine='python')
                except Exception:
                    return pd.DataFrame()
        else:
            # Try default location
            default_raw = self.output_dir / "raw_metrics.csv"
            if not default_raw.exists():
                return pd.DataFrame()
            try:
                df = pd.read_csv(
                    default_raw,
                    quoting=1,
                    escapechar=None,
                    doublequote=True,
                    on_bad_lines='skip',
                    engine='python'
                )
            except Exception:
                try:
                    df = pd.read_csv(default_raw, on_bad_lines='skip', engine='python')
                except Exception:
                    return pd.DataFrame()
        
        if df.empty:
            return pd.DataFrame()
        
        # Convert numeric columns to proper numeric types
        numeric_columns = ['input_tokens', 'output_tokens', 'latency_ms', 
                          'cost_usd_input', 'cost_usd_output', 'cost_usd_total']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Convert boolean columns
        if 'json_valid' in df.columns:
            df['json_valid'] = pd.to_numeric(df['json_valid'], errors='coerce').fillna(0).astype(bool)
        
        # Filter out errors for latency calculations
        success_df = df[df["status"] == "success"].copy()
        
        # Group by model
        grouped = success_df.groupby(["model_name"], dropna=False)
        
        # Calculate aggregations
        agg_data = []
        for model_name, group in grouped:
            if group.empty:
                continue
            
            json_valid_count = group["json_valid"].sum() if "json_valid" in group.columns else 0
            total_count = len(group)
            
            agg_data.append({
                "model_name": model_name,
                "count": total_count,
                "success_count": total_count,  # Already filtered
                "error_count": len(df[(df["model_name"] == model_name) & (df["status"] == "error")]),
                "avg_input_tokens": round(group["input_tokens"].mean(), 1),
                "avg_output_tokens": round(group["output_tokens"].mean(), 1),
                "p50_latency_ms": round(percentile(group["latency_ms"], 0.50), 1),
                "p95_latency_ms": round(percentile(group["latency_ms"], 0.95), 1),
                "p99_latency_ms": round(percentile(group["latency_ms"], 0.99), 1),
                "min_latency_ms": round(group["latency_ms"].min(), 1),
                "max_latency_ms": round(group["latency_ms"].max(), 1),
                "json_valid_pct": round((json_valid_count / total_count * 100.0) if total_count > 0 else 0.0, 2),
                "avg_cost_usd_per_request": round(group["cost_usd_total"].mean(), 6),
                "total_cost_usd": round(group["cost_usd_total"].sum(), 6),
            })
        
        agg_df = pd.DataFrame(agg_data)
        
        if not agg_df.empty:
            # Sort by model name
            agg_df = agg_df.sort_values("model_name").reset_index(drop=True)
            
            # Save to CSV
            agg_df.to_csv(self.comparison_csv_path, index=False)
        
        return agg_df
    
    def get_comparison_df(self) -> pd.DataFrame:
        """Load existing comparison report."""
        if not self.comparison_csv_path.exists():
            return pd.DataFrame()
        
        try:
            return pd.read_csv(
                self.comparison_csv_path,
                quoting=1,
                escapechar=None,
                doublequote=True,
                on_bad_lines='skip',
                engine='python'
            )
        except Exception:
            try:
                return pd.read_csv(self.comparison_csv_path, on_bad_lines='skip', engine='python')
            except Exception:
                return pd.DataFrame()


def aggregate_metrics(raw_csv_path: str, out_csv_path: str) -> pd.DataFrame:
    """Legacy function for backward compatibility."""
    generator = ReportGenerator(Path(out_csv_path).parent)
    return generator.generate_report(raw_csv_path=raw_csv_path)


