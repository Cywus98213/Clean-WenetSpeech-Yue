from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse


def safe_filename(name: str) -> str:
    """Return a filesystem-safe filename fragment from the given string."""
    return re.sub(r"[^a-zA-Z0-9_.\-]", "_", name).strip("_.-") or "file"


ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
LITERAL_ANSI_RE = re.compile(r"\[(?:\d+;)*\d*m")


def clean_error_message(message: str | None) -> str:
    """Remove terminal color codes and leading ERROR: prefix from yt-dlp messages."""
    if message is None:
        return ""
    text = ANSI_ESCAPE_RE.sub("", str(message))
    text = LITERAL_ANSI_RE.sub("", text).strip()
    if text.upper().startswith("ERROR:"):
        text = text[6:].strip()
    return text


def extract_video_id(link: str) -> str:
    """Extract a stable video ID from a variety of online video links."""
    if not isinstance(link, str):
        raise ValueError("link must be a string")

    # Bilibili BV IDs are stable and unique.
    bv_match = re.search(r"BV[0-9A-Za-z]+", link)
    if bv_match:
        return bv_match.group(0)

    # Douyin and Xigua use numeric IDs in the URL.
    dy_match = re.search(r"douyin\.com/(?:video|user/.+?/video)/(\d+)", link)
    if dy_match:
        return dy_match.group(1)

    xi_match = re.search(r"ixigua\.com/(?:video/)?(\d+)", link)
    if xi_match:
        return xi_match.group(1)

    # Generic fallback for URLs like /video/..., /v/.../play/..., or query strings.
    generic_match = re.search(r"/(?:video|v|play)/([A-Za-z0-9_\-]+)", link)
    if generic_match:
        return generic_match.group(1)

    # Last fallback: stable hash of the entire link.
    return hashlib.md5(link.encode("utf-8")).hexdigest()[:16]


def extract_bilibili_page(link: str) -> str | None:
    """Return the Bilibili multi-part page number from a URL, if present."""
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    for key in ("p", "page"):
        values = query.get(key)
        if values and str(values[0]).strip().isdigit():
            return str(int(values[0]))
    return None


def extract_audio_cache_key(link: str) -> str:
    """Return a cache key that distinguishes different audio sources for the same video ID.

    Bilibili anthology links such as ``...?p=354`` must not share one cached file.
    """
    if not isinstance(link, str):
        raise ValueError("link must be a string")

    video_id = extract_video_id(link)
    page = extract_bilibili_page(link)
    if page and re.search(r"BV[0-9A-Za-z]+", link):
        return f"{video_id}_p{page}"
    return video_id


def parse_time_stamp(
    time_stamp: str | None,
    duration: float | str | None = None,
) -> Tuple[Optional[float], Optional[float]]:
    """Parse a timestamp into (start_seconds, end_seconds).

    Accepts timestamps in the form "start_end" or a single start value with
    a duration supplied separately.
    """
    if not time_stamp:
        return None, None

    if not isinstance(time_stamp, str):
        time_stamp = str(time_stamp)

    parts = time_stamp.strip().split("_")
    if len(parts) == 2:
        try:
            start = float(parts[0])
            end = float(parts[1])
        except ValueError:
            return None, None
        return (start, end) if end > start else (None, None)

    try:
        start = float(time_stamp.strip())
    except ValueError:
        return None, None

    if duration is None or duration == "":
        return None, None

    try:
        duration_value = float(duration)
    except (TypeError, ValueError):
        return None, None

    end = start + duration_value
    return (start, end) if end > start else (None, None)


def timestamp_label_for_filename(
    time_stamp: str | None,
    start: float | None = None,
    end: float | None = None,
) -> str:
    """Build a stable timestamp fragment for clip filenames."""
    if time_stamp is not None and str(time_stamp).strip():
        label = safe_filename(str(time_stamp).strip().replace(".", "_"))
        if label:
            return label
    if start is not None and end is not None:
        return f"{int(round(start * 1000))}_{int(round(end * 1000))}"
    return "unknown_ts"


def build_clip_output_path(
    clip_dir: Path,
    *,
    cache_key: str,
    key: str,
    time_stamp: str | None,
    start: float | None = None,
    end: float | None = None,
) -> Path:
    """Unique clip path per source + timestamp segment + dataset row."""
    source_part = safe_filename(cache_key or "source")
    key_part = safe_filename(key or "clip")

    if start is not None and end is not None:
        ts_part = f"{int(round(start * 1000))}_{int(round(end * 1000))}"
    else:
        ts_part = timestamp_label_for_filename(time_stamp, start, end)

    return clip_dir / f"{source_part}_{ts_part}_{key_part}.mp3"


def find_cached_audio(
    cache_key: str,
    cache_dir: Path,
    extensions: tuple[str, ...] = (".mp3", ".m4a", ".webm", ".aac", ".wav"),
) -> Optional[Path]:
    """Return the cached full audio path for a cache key, if any."""
    safe_id = safe_filename(cache_key)
    for ext in extensions:
        candidate = cache_dir / f"{safe_id}{ext}"
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


MIN_VALID_CLIP_BYTES = 1024


def probe_audio_duration(path: Path) -> Optional[float]:
    """Return audio duration in seconds using ffprobe, if available."""
    import subprocess

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        duration = float(result.stdout.strip())
        return duration if duration > 0 else None
    except (subprocess.CalledProcessError, ValueError, OSError):
        return None
