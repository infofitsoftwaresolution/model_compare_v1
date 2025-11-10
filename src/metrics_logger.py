"""Metrics logger: persists per-request metrics to CSV/SQLite."""

from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd


class MetricsLogger:
    """Handles logging and persistence of evaluation metrics."""
    
    def __init__(self, output_dir: Union[str, Path]):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_csv_path = self.output_dir / "raw_metrics.csv"
    
    def log_metrics(self, metrics_list: List[Dict[str, Any]]) -> None:
        """
        Log metrics to CSV file.
        
        Args:
            metrics_list: List of metric dictionaries
        """
        if not metrics_list:
            return
        
        df = pd.DataFrame(metrics_list)
        
        # Convert numeric columns to proper numeric types before saving
        numeric_columns = ['input_tokens', 'output_tokens', 'latency_ms', 
                          'cost_usd_input', 'cost_usd_output', 'cost_usd_total']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Convert boolean columns
        if 'json_valid' in df.columns:
            # Handle various boolean representations
            df['json_valid'] = df['json_valid'].astype(str).replace({
                'True': True, 'False': False, 
                'true': True, 'false': False,
                '1': True, '0': False,
                'TRUE': True, 'FALSE': False
            })
            df['json_valid'] = pd.to_numeric(df['json_valid'], errors='coerce').fillna(False).astype(bool)
        
        # Ensure consistent column order
        expected_columns = [
            "timestamp", "run_id", "model_name", "model_id", "prompt_id",
            "input_tokens", "output_tokens", "latency_ms",
            "json_valid", "error", "status",
            "cost_usd_input", "cost_usd_output", "cost_usd_total"
        ]
        
        # Add input_prompt and response columns if present
        if "input_prompt" in df.columns:
            expected_columns.append("input_prompt")
        if "response" in df.columns:
            expected_columns.append("response")
        
        # If file exists, read existing columns to ensure compatibility
        existing_columns = []
        if self.raw_csv_path.exists():
            try:
                # Try to read just the header first
                existing_df = pd.read_csv(
                    self.raw_csv_path, 
                    nrows=0,  # Just read header
                    quoting=1,  # QUOTE_ALL
                    engine='python'  # More lenient engine
                )
                existing_columns = list(existing_df.columns)
            except Exception:
                # If file is corrupted, try to read with error handling
                try:
                    existing_df = pd.read_csv(
                        self.raw_csv_path,
                        quoting=1,
                        on_bad_lines='skip',
                        engine='python'
                    )
                    existing_columns = list(existing_df.columns) if not existing_df.empty else []
                except Exception:
                    # If still failing, we'll recreate it
                    existing_columns = []
        
        # Merge expected columns with existing columns
        if existing_columns:
            # Use union of columns to ensure compatibility
            all_columns = list(dict.fromkeys(existing_columns + expected_columns))
        else:
            all_columns = expected_columns
        
        # Reorder and add missing columns
        for col in all_columns:
            if col not in df.columns:
                df[col] = None
        
        # Select columns in the correct order
        df = df[[col for col in all_columns if col in df.columns]]
        
        # Append or create CSV - pandas automatically handles quoting of fields with commas
        # Use proper CSV quoting to handle multi-line fields and special characters
        header = not self.raw_csv_path.exists()
        
        # If file exists and we're appending, verify it's readable first
        if not header:
            try:
                # Try to read a small sample to verify file is valid
                test_read = pd.read_csv(
                    self.raw_csv_path,
                    nrows=1,
                    quoting=1,
                    engine='python'
                )
            except Exception as e:
                # If file is corrupted, backup it and start fresh
                import shutil
                backup_path = self.raw_csv_path.with_suffix('.csv.backup')
                try:
                    shutil.copy2(self.raw_csv_path, backup_path)
                    self.raw_csv_path.unlink()  # Remove corrupted file
                    header = True  # Write header for new file
                except Exception:
                    # If backup fails, just try to overwrite
                    header = True
        
        # Write or append to CSV
        try:
            df.to_csv(
                self.raw_csv_path, 
                mode="a" if not header else "w", 
                header=header, 
                index=False, 
                quoting=1,  # QUOTE_ALL - quote all fields
                escapechar=None,  # Don't use escapechar, rely on quoting
                doublequote=True,  # Double quotes within quoted fields
                lineterminator='\n'  # Explicit line terminator
            )
        except Exception as e:
            # If append fails (e.g., due to corrupted existing file), 
            # try to read existing data, combine, and rewrite
            if not header:
                try:
                    existing_df = self.get_metrics_df()
                    if not existing_df.empty:
                        # Combine existing and new data
                        combined_df = pd.concat([existing_df, df], ignore_index=True)
                        # Remove duplicates based on timestamp and model_name
                        combined_df = combined_df.drop_duplicates(
                            subset=['timestamp', 'model_name', 'prompt_id'] if 'prompt_id' in combined_df.columns 
                            else ['timestamp', 'model_name'],
                            keep='last'
                        )
                        # Write combined data
                        combined_df.to_csv(
                            self.raw_csv_path,
                            mode="w",
                            header=True,
                            index=False,
                            quoting=1,
                            escapechar=None,
                            doublequote=True,
                            lineterminator='\n'
                        )
                    else:
                        # If we can't read existing data, just write new data
                        df.to_csv(
                            self.raw_csv_path,
                            mode="w",
                            header=True,
                            index=False,
                            quoting=1,
                            escapechar=None,
                            doublequote=True,
                            lineterminator='\n'
                        )
                except Exception:
                    # Final fallback: just write new data with header
                    df.to_csv(
                        self.raw_csv_path,
                        mode="w",
                        header=True,
                        index=False,
                        quoting=1,
                        escapechar=None,
                        doublequote=True,
                        lineterminator='\n'
                    )
            else:
                # If we were creating a new file, just write it
                df.to_csv(
                    self.raw_csv_path,
                    mode="w",
                    header=True,
                    index=False,
                    quoting=1,
                    escapechar=None,
                    doublequote=True,
                    lineterminator='\n'
                )
    
    def get_metrics_df(self) -> pd.DataFrame:
        """Load existing metrics from CSV."""
        if not self.raw_csv_path.exists():
            return pd.DataFrame()
        
        # Read CSV with proper handling of multi-line fields
        try:
            return pd.read_csv(
                self.raw_csv_path,
                quoting=1,  # QUOTE_ALL
                escapechar=None,
                doublequote=True,
                on_bad_lines='skip'  # Skip problematic lines instead of failing
            )
        except pd.errors.ParserError as e:
            # If CSV is corrupted, try to read it with more lenient settings
            try:
                return pd.read_csv(
                    self.raw_csv_path,
                    quoting=1,
                    on_bad_lines='skip',
                    engine='python'  # Use Python engine which is more lenient
                )
            except Exception:
                # If still failing, return empty DataFrame
                return pd.DataFrame()


def append_metrics_csv(df: pd.DataFrame, out_csv: Union[str, Path]) -> None:
    """Append metrics DataFrame to CSV file."""
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = not out_path.exists()
    df.to_csv(out_path, mode="a", header=header, index=False)


