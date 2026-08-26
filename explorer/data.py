from __future__ import annotations

import pandas as pd

from audio_utils import clean_error_message
from explorer.config import CLIP_CSV, FAILED_CSV


def load_csv(csv_path) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path)


def load_clip_data() -> pd.DataFrame:
    return load_csv(CLIP_CSV)


def load_download_failures() -> pd.DataFrame:
    failed_df = load_csv(FAILED_CSV)
    if failed_df.empty:
        return failed_df
    failed_df = failed_df.copy()
    if "error" not in failed_df.columns:
        failed_df["error"] = "unknown"
    failed_df["error"] = failed_df["error"].map(clean_error_message)
    return failed_df
