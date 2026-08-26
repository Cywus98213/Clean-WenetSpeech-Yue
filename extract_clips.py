from __future__ import annotations

import argparse
import csv
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from audio_utils import (
    MIN_VALID_CLIP_BYTES,
    build_clip_output_path,
    extract_audio_cache_key,
    extract_video_id,
    find_cached_audio,
    parse_time_stamp,
    probe_audio_duration,
    clean_error_message,
)


# ==================== CONFIGURATION ====================
DEFAULT_CSV_PATH = Path("success") / "success_links.csv"
DEFAULT_CACHE_DIR = Path("success")
DEFAULT_CLIP_DIR = Path("speech_clips")
DEFAULT_SUCCESS_DIR = Path("success")
DEFAULT_FAILED_DIR = Path("failed")
CLIP_CSV_NAME = "clip_view.csv"
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_WORKERS = 8
DEFAULT_LIMIT = 0  # Set to a positive integer to only process that many rows.
DEFAULT_QUIET = False
# ================================================


def configure_logger(quiet: bool) -> None:
    level = logging.WARNING if quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_ffmpeg_command(
    source_path: Path,
    output_path: Path,
    start: float,
    end: float,
    extra_args: list[str] | None = None,
) -> list[str]:
    duration = end - start
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_path),
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-acodec",
        "libmp3lame",
        "-q:a",
        "2",
        str(output_path),
    ]
    if extra_args:
        command = command[:6] + extra_args + command[6:]
    return command


def resolve_output_path(path_value: str | Path | None, project_root: Path | None = None) -> Path:
    if path_value is None:
        return PROJECT_ROOT / DEFAULT_CLIP_DIR
    path = Path(path_value)
    if path.is_absolute():
        return path
    root = project_root or PROJECT_ROOT
    return root / path


def make_project_relative(path_value: str | Path | None, project_root: Path) -> str | None:
    if path_value is None:
        return None

    raw_path = str(path_value).strip()
    if not raw_path:
        return None

    path = Path(raw_path)
    if not path.is_absolute():
        return raw_path.replace("\\", "/")

    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def write_clip_csv(
    successful_rows: list[dict[str, Any]],
    output_csv: Path,
    project_root: Path,
    columns: list[str],
) -> None:
    """Write successful clip rows only, without status/error columns."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    all_rows = [normalize_output_row(row, project_root) for row in successful_rows]

    if all_rows:
        pd.DataFrame(all_rows).to_csv(output_csv, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    else:
        pd.DataFrame(columns=list(columns) + ["local_audio_path"]).to_csv(
            output_csv, index=False, encoding="utf-8"
        )


def normalize_output_row(row: dict[str, Any], project_root: Path) -> dict[str, Any]:
    normalized_row = dict(row)
    if "local_audio_path" in normalized_row:
        normalized_row["local_audio_path"] = make_project_relative(normalized_row["local_audio_path"], project_root)
    if "full_audio_path" in normalized_row:
        normalized_row["full_audio_path"] = make_project_relative(normalized_row["full_audio_path"], project_root)
    return normalized_row


def cut_clip(
    key: str,
    cache_key: str,
    time_stamp: str,
    source_path: Path,
    start: float,
    end: float,
    clip_dir: Path,
) -> tuple[str, bool, str | None]:
    source_duration = probe_audio_duration(source_path)
    if source_duration is not None:
        if start >= source_duration:
            return (
                key,
                False,
                f"clip starts at {start:.3f}s but source audio is only {source_duration:.3f}s long",
            )
        if end > source_duration + 0.05:
            return (
                key,
                False,
                f"clip ends at {end:.3f}s but source audio is only {source_duration:.3f}s long",
            )

    clip_path = build_clip_output_path(
        clip_dir,
        cache_key=cache_key,
        key=key,
        time_stamp=time_stamp,
        start=start,
        end=end,
    )

    clip_dir.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(source_path, clip_path, start, end)

    try:
        subprocess.run(command, check=True, capture_output=True)
        if not clip_path.exists():
            return key, False, "ffmpeg completed but output file is missing"

        clip_size = clip_path.stat().st_size
        if clip_size < MIN_VALID_CLIP_BYTES:
            clip_path.unlink(missing_ok=True)
            return key, False, f"output file too small ({clip_size} bytes) to be valid audio"

        clip_duration = probe_audio_duration(clip_path)
        if clip_duration is None or clip_duration < 0.1:
            clip_path.unlink(missing_ok=True)
            return key, False, "output file is not valid playable audio"

        return key, True, str(clip_path)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        clip_path.unlink(missing_ok=True)
        return key, False, f"ffmpeg failed: {stderr.strip()}"
    except Exception as exc:
        clip_path.unlink(missing_ok=True)
        return key, False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract timestamped audio clips from pre-downloaded full audio files. "
            "By default this reads success/success_links.csv and looks for source audio in success/."
        )
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=str(DEFAULT_CSV_PATH),
        help=(
            f"Input CSV file containing 'key', 'link', and 'time_stamp' columns. "
            f"Defaults to {DEFAULT_CSV_PATH}"
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help=f"Directory containing full downloaded audio files. Defaults to {DEFAULT_CACHE_DIR}",
    )
    parser.add_argument(
        "--clip-dir",
        type=Path,
        default=DEFAULT_CLIP_DIR,
        help=f"Directory where clipped MP3 files will be written. Defaults to {DEFAULT_CLIP_DIR}",
    )
    parser.add_argument(
        "--success-dir",
        type=Path,
        default=DEFAULT_SUCCESS_DIR,
        help=f"Directory where success CSV output is written. Defaults to {DEFAULT_SUCCESS_DIR}",
    )
    parser.add_argument(
        "--failed-dir",
        type=Path,
        default=DEFAULT_FAILED_DIR,
        help=f"Directory where failure CSV output is written. Defaults to {DEFAULT_FAILED_DIR}",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel ffmpeg jobs. Defaults to {DEFAULT_WORKERS}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"If positive, only process the first N rows of the CSV. Defaults to {DEFAULT_LIMIT}",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=DEFAULT_QUIET,
        help=f"Reduce logging output. Defaults to {DEFAULT_QUIET}",
    )
    args = parser.parse_args()

    configure_logger(args.quiet)

    try:
        df = pd.read_csv(args.csv_path)
    except FileNotFoundError:
        logging.error("Input CSV file does not exist: %s", args.csv_path)
        return 1
    except Exception as exc:
        logging.error("Failed to read CSV: %s", exc)
        return 1

    missing_columns = [col for col in ("key", "link", "time_stamp") if col not in df.columns]
    if missing_columns:
        logging.error("CSV is missing required columns: %s", ", ".join(missing_columns))
        return 1

    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    df = df[df["link"].notna() & df["key"].notna()].copy()
    df["video_id"] = df["link"].astype(str).apply(extract_video_id)
    df["cache_key"] = df["link"].astype(str).apply(extract_audio_cache_key)
    candidates: list[tuple[int, dict[str, Any]]] = [
        (index, row.to_dict())
        for index, row in df.iterrows()
    ]

    if not candidates:
        logging.warning("No rows to process after removing empty keys or links.")
        return 0

    logging.info("Processing %d timestamped clips.", len(candidates))

    successful_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []
    project_root = Path(__file__).resolve().parent
    clip_dir = resolve_output_path(args.clip_dir, project_root)
    cache_dir = resolve_output_path(args.cache_dir, project_root)
    clip_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    def work(item: tuple[int, dict[str, Any]]) -> tuple[int, dict[str, Any], bool, str | None]:
        index, row = item
        cache_key = str(row.get("cache_key") or extract_audio_cache_key(str(row["link"])))

        source_path = None
        full_audio_path = row.get("full_audio_path")
        if full_audio_path and isinstance(full_audio_path, str):
            raw_path = full_audio_path.strip()
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = (project_root / candidate).resolve()
            if candidate.exists() and candidate.is_file():
                source_path = candidate

        if source_path is None:
            source_path = find_cached_audio(cache_key, cache_dir)
        if source_path is None:
            return index, row, False, f"missing full audio file for cache key {cache_key}"

        start, end = parse_time_stamp(str(row["time_stamp"]), row.get("duration"))
        if start is None or end is None:
            return index, row, False, "invalid time_stamp or duration"

        key = str(row["key"])
        time_stamp = str(row["time_stamp"])
        clip_key, ok, result = cut_clip(
            key,
            cache_key,
            time_stamp,
            source_path,
            start,
            end,
            clip_dir,
        )
        if ok:
            row["local_audio_path"] = result
            row["clip_start_sec"] = start
            row["clip_end_sec"] = end
            return index, row, True, result

        return index, row, False, result or "unknown failure"

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(work, item): item for item in candidates}
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Cutting clips",
            unit="clip",
            dynamic_ncols=True,
            smoothing=0.3,
        ):
            _, row, success_flag, detail = future.result()
            if success_flag:
                successful_rows.append(row)
            else:
                failure_row = row.copy()
                failure_row["error"] = clean_error_message(detail)
                failed_rows.append(failure_row)

    clip_csv = clip_dir / CLIP_CSV_NAME
    write_clip_csv(successful_rows, clip_csv, project_root, list(df.columns))

    print("\n=== CLIP EXTRACTION SUMMARY ===")
    print(f"Success: {len(successful_rows)}")
    print(f"Failed: {len(failed_rows)}")
    print(f"Clip CSV: {clip_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
