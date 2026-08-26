from __future__ import annotations

import logging


class NullLogger:
    """Custom logger for yt-dlp that suppresses all output."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def configure_logger(quiet: bool) -> None:
    """Set up logging level. If quiet, suppress almost everything."""
    level = logging.ERROR if quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for name in ["yt_dlp", "yt_dlp.extractor", "yt_dlp.downloader", "yt_dlp.postprocessor"]:
        logging.getLogger(name).setLevel(logging.ERROR)
