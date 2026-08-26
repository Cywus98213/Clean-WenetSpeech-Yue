from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from download.config import (
    DEFAULT_COOKIES_FILE,
    DEFAULT_CSV_PATH,
    DEFAULT_FAILED_DIR,
    DEFAULT_FRAGMENT_WORKERS,
    DEFAULT_LIMIT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_QUIET,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_USE_ARIA2,
    DEFAULT_WORKERS,
)
from download.logging_utils import configure_logger
from download.pipeline import run_downloads


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download full audio for unique video links and create a mapping CSV."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=str(DEFAULT_CSV_PATH),
        help=f"Input CSV file. Defaults to {DEFAULT_CSV_PATH}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"If positive, only process the first N rows. Defaults to {DEFAULT_LIMIT}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for downloaded audio files. Defaults to {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--failed-dir",
        type=Path,
        default=DEFAULT_FAILED_DIR,
        help=f"Directory for failed report CSV. Defaults to {DEFAULT_FAILED_DIR}",
    )
    parser.add_argument(
        "--cookies-file",
        type=Path,
        default=DEFAULT_COOKIES_FILE,
        help=f"Optional cookies file. Defaults to {DEFAULT_COOKIES_FILE}",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Concurrent downloads. Defaults to {DEFAULT_WORKERS}",
    )
    parser.add_argument(
        "--fragment-workers",
        type=int,
        default=DEFAULT_FRAGMENT_WORKERS,
        help=f"Fragment downloads per video. Defaults to {DEFAULT_FRAGMENT_WORKERS}",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Retries on failure. Defaults to {DEFAULT_RETRIES}",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_RETRY_DELAY,
        help=f"Delay between retries. Defaults to {DEFAULT_RETRY_DELAY}",
    )
    parser.add_argument(
        "--use-aria2",
        action="store_true",
        default=DEFAULT_USE_ARIA2,
        help=f"Use aria2c. Defaults to {DEFAULT_USE_ARIA2}",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=DEFAULT_QUIET,
        help=f"Suppress all non-essential output. Defaults to {DEFAULT_QUIET}",
    )
    return parser


def resolve_project_path(path: Path, project_root: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logger(args.quiet)

    project_root = Path(__file__).resolve().parent.parent
    output_dir = resolve_project_path(args.output_dir, project_root)
    failed_dir = resolve_project_path(args.failed_dir, project_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    csv_path = Path(args.csv_path)
    if not csv_path.is_absolute():
        csv_path = project_root / csv_path

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        logging.error("Input CSV file does not exist: %s", csv_path)
        return 1
    except Exception as exc:
        logging.error("Failed to read CSV: %s", exc)
        return 1

    if "link" not in df.columns:
        logging.error("CSV must contain a 'link' column.")
        return 1

    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    cookies_file = args.cookies_file
    if not cookies_file.is_absolute():
        cookies_file = project_root / cookies_file

    result = run_downloads(
        df=df,
        output_dir=output_dir,
        failed_dir=failed_dir,
        cookies_file=cookies_file,
        workers=args.workers,
        fragment_workers=args.fragment_workers,
        retries=args.retries,
        retry_delay=args.retry_delay,
        use_aria2=args.use_aria2,
        quiet=args.quiet,
    )

    print("Success report saved.")
    print("Failed report saved.")

    if not args.quiet:
        print("\n=== DOWNLOAD SUMMARY ===")
        print(f"Original rows processed: {len(result['df'])}")
        print(f"Unique videos downloaded: {len(result['unique_links'])}")
        print(f"Successful video downloads: {len(result['success'])}")
        print(f"Failed video downloads: {len(result['failed'])}")
        print(f"Successful rows: {len(result['success_records'])}")
        print(f"Failed rows: {len(result['failed_records'])}")
        print(f"Success report saved: {result['success_csv_path']}")
        print(f"Failed report saved: {result['failed_csv_path']}")

    return 0
