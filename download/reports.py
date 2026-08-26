from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

from audio_utils import extract_audio_cache_key, clean_error_message


def classify_row(
    row: pd.Series,
    cache_key_to_path: dict[str, str | None],
    failed_by_cache_key: dict[str, str],
) -> tuple[dict[str, Any], bool]:
    """Return a normalized row record and whether it counts as success."""
    record = row.to_dict()
    cache_key = str(row.get("cache_key", "") or "").strip()
    if not cache_key:
        cache_key = extract_audio_cache_key(str(row.get("link", "") or ""))
    record["cache_key"] = cache_key

    path = cache_key_to_path.get(cache_key)

    if path:
        record["full_audio_path"] = path
        return record, True

    record.pop("full_audio_path", None)
    if cache_key in failed_by_cache_key:
        record["error"] = clean_error_message(failed_by_cache_key[cache_key])
    elif cache_key in cache_key_to_path:
        record["error"] = "download_failed"
    else:
        record["error"] = "video_not_attempted"
    return record, False


def build_output_records(
    df: pd.DataFrame,
    cache_key_to_path: dict[str, str | None],
    failed_by_cache_key: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split input rows into success and failed report records."""
    success_records: list[dict[str, Any]] = []
    failed_records: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        link = str(row.get("link", "") or "").strip()
        if not link or link.lower() == "nan":
            record = row.to_dict()
            record.pop("full_audio_path", None)
            record["error"] = "missing_link"
            failed_records.append(record)
            continue

        record, is_success = classify_row(row, cache_key_to_path, failed_by_cache_key)
        if is_success:
            success_records.append(record)
        else:
            failed_records.append(record)

    return success_records, failed_records


def write_report_csvs(
    df: pd.DataFrame,
    success_records: list[dict[str, Any]],
    failed_records: list[dict[str, Any]],
    success_csv_path: Path,
    failed_csv_path: Path,
) -> None:
    """Always write both CSV reports, matching the clip extractor behavior."""
    success_csv_path.parent.mkdir(parents=True, exist_ok=True)
    failed_csv_path.parent.mkdir(parents=True, exist_ok=True)

    success_columns = list(df.columns)
    if "cache_key" not in success_columns:
        success_columns.append("cache_key")
    if "full_audio_path" not in success_columns:
        success_columns.append("full_audio_path")

    failed_columns = list(df.columns)
    if "cache_key" not in failed_columns:
        failed_columns.append("cache_key")
    if "error" not in failed_columns:
        failed_columns.append("error")
    failed_columns = [col for col in failed_columns if col != "full_audio_path"]

    if success_records:
        pd.DataFrame(success_records).to_csv(
            success_csv_path,
            index=False,
            encoding="utf-8",
            quoting=csv.QUOTE_MINIMAL,
        )
    else:
        pd.DataFrame(columns=success_columns).to_csv(
            success_csv_path,
            index=False,
            encoding="utf-8",
        )

    if failed_records:
        cleaned_failed_records = []
        for record in failed_records:
            cleaned = dict(record)
            cleaned.pop("full_audio_path", None)
            cleaned_failed_records.append(cleaned)
        pd.DataFrame(cleaned_failed_records).to_csv(
            failed_csv_path,
            index=False,
            encoding="utf-8",
            quoting=csv.QUOTE_MINIMAL,
        )
    else:
        pd.DataFrame(columns=failed_columns).to_csv(
            failed_csv_path,
            index=False,
            encoding="utf-8",
        )
