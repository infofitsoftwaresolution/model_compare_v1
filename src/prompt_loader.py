"""Prompt loader: reads CSV prompts and validates minimal schema."""

from pathlib import Path
import pandas as pd


REQUIRED_COLUMNS = ["prompt"]


def load_prompts(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    if "prompt_id" not in df.columns:
        df.insert(0, "prompt_id", range(1, len(df) + 1))
    return df


