"""Modular video audio downloader package."""

from download.config import (
    DEFAULT_CSV_PATH,
    DEFAULT_FAILED_DIR,
    DEFAULT_OUTPUT_DIR,
    FAILED_CSV_NAME,
    SUCCESS_CSV_NAME,
)

__all__ = [
    "DEFAULT_CSV_PATH",
    "DEFAULT_FAILED_DIR",
    "DEFAULT_OUTPUT_DIR",
    "FAILED_CSV_NAME",
    "SUCCESS_CSV_NAME",
    "main",
]


def main(*args, **kwargs):
    from download.cli import main as cli_main

    return cli_main(*args, **kwargs)
