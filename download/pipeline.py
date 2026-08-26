from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from audio_utils import extract_audio_cache_key, extract_video_id
from download.config import FAILED_CSV_NAME, SUCCESS_CSV_NAME
from download.reports import build_output_records, write_report_csvs
from download.ydl_client import build_ydl_options, download_audio


def run_downloads(
    df: pd.DataFrame,
    output_dir: Path,
    failed_dir: Path,
    cookies_file: Path | None,
    workers: int,
    fragment_workers: int,
    retries: int,
    retry_delay: float,
    use_aria2: bool,
    quiet: bool,
) -> dict[str, Any]:
    """Download unique videos and write success/failed CSV reports."""
    df = df.copy()
    df["video_id"] = df["link"].fillna("").astype(str).apply(extract_video_id)
    df["cache_key"] = df["link"].fillna("").astype(str).apply(extract_audio_cache_key)

    unique_links = (
        df[df["cache_key"].notna() & (df["cache_key"] != "")]
        .drop_duplicates(subset=["cache_key"])
        .reset_index(drop=True)
    )

    if not quiet:
        logging.info("Found %d rows and %d unique audio sources.", len(df), len(unique_links))

    ydl_opts = build_ydl_options(
        outdir=output_dir,
        use_aria2=use_aria2,
        fragment_workers=fragment_workers,
        cookies_file=cookies_file if cookies_file and cookies_file.exists() else None,
        quiet=quiet,
    )

    cache_key_to_path: dict[str, str | None] = {}
    success: list[tuple[str, str]] = []
    failed: list[tuple[str, str, str]] = []

    with ThreadPoolExecutor(max_workers=max(4, workers)) as executor:
        futures = {
            executor.submit(
                download_audio,
                row["link"],
                row["cache_key"],
                output_dir,
                ydl_opts,
                retries,
                retry_delay,
            ): row
            for _, row in unique_links.iterrows()
        }

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Downloading full audio",
            unit="video",
            dynamic_ncols=True,
            smoothing=0.3,
        ):
            row = futures[future]
            cache_key = str(row["cache_key"])
            try:
                success_flag, result = future.result()
                if success_flag and result:
                    cache_key_to_path[cache_key] = result
                    success.append((cache_key, result))
                else:
                    cache_key_to_path[cache_key] = None
                    failed.append((cache_key, str(row["link"]), result or "unknown"))
            except Exception as exc:
                cache_key_to_path[cache_key] = None
                failed.append((cache_key, str(row["link"]), str(exc)))

    failed_by_cache_key = {cache_key: error for cache_key, _, error in failed}
    success_records, failed_records = build_output_records(df, cache_key_to_path, failed_by_cache_key)

    success_csv_path = output_dir / SUCCESS_CSV_NAME
    failed_csv_path = failed_dir / FAILED_CSV_NAME
    write_report_csvs(df, success_records, failed_records, success_csv_path, failed_csv_path)

    return {
        "df": df,
        "unique_links": unique_links,
        "success": success,
        "failed": failed,
        "success_records": success_records,
        "failed_records": failed_records,
        "success_csv_path": success_csv_path,
        "failed_csv_path": failed_csv_path,
    }
