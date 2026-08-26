"""Backward-compatible entry point for the modular downloader."""

from download.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
