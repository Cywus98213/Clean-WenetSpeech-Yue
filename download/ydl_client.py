from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yt_dlp

from audio_utils import safe_filename, clean_error_message
from download.logging_utils import NullLogger


def build_ydl_options(
    outdir: Path,
    use_aria2: bool,
    fragment_workers: int,
    cookies_file: Path | None,
    quiet: bool,
) -> dict[str, Any]:
    outtmpl = str(outdir / "%(id)s.%(ext)s")
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": quiet,
        "no_warnings": quiet,
        "logger": NullLogger(),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "concurrent_fragment_downloads": max(1, fragment_workers),
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
    }

    if use_aria2:
        options["external_downloader"] = "aria2c"
        options["external_downloader_args"] = ["-x", "8", "-s", "8", "-k", "1M"]

    if cookies_file and cookies_file.exists():
        options["cookiefile"] = str(cookies_file)

    return options


def download_audio(
    link: str,
    cache_key: str,
    cache_dir: Path,
    ydl_opts: dict[str, Any],
    retries: int,
    retry_delay: float,
) -> tuple[bool, str | None]:
    safe_id = safe_filename(cache_key)
    out_path_base = cache_dir / safe_id
    cached_mp3 = out_path_base.with_suffix(".mp3")
    if cached_mp3.exists() and cached_mp3.stat().st_size > 0:
        return True, str(cached_mp3)

    ydl_opts = dict(ydl_opts)
    ydl_opts["outtmpl"] = str(cache_dir / f"{safe_id}.%(ext)s")
    ydl_opts["paths"] = {"home": str(cache_dir)}

    for attempt in range(1, retries + 2):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])

            if cached_mp3.exists() and cached_mp3.stat().st_size > 0:
                return True, str(cached_mp3)

            for extension in [".m4a", ".webm", ".aac", ".wav"]:
                candidate = out_path_base.with_suffix(extension)
                if candidate.exists() and candidate.stat().st_size > 0:
                    return True, str(candidate)

            return False, "download completed but no output file was produced"
        except Exception as exc:
            if attempt <= retries:
                time.sleep(retry_delay)
                continue
            return False, clean_error_message(str(exc))
