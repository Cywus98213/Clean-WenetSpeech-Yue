from __future__ import annotations

from pathlib import Path

DEFAULT_CSV_PATH = Path("wenetspeech_refined_clean.csv")
DEFAULT_LIMIT = 20000
DEFAULT_OUTPUT_DIR = Path("success")
DEFAULT_FAILED_DIR = Path("failed")
DEFAULT_COOKIES_FILE = Path("cookies.txt")
DEFAULT_WORKERS = 8
DEFAULT_FRAGMENT_WORKERS = 5
DEFAULT_RETRIES = 2
DEFAULT_RETRY_DELAY = 5.0
DEFAULT_USE_ARIA2 = False
DEFAULT_QUIET = False

SUCCESS_CSV_NAME = "success_links.csv"
FAILED_CSV_NAME = "failed_links.csv"
