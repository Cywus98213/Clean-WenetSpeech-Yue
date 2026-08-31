from __future__ import annotations

import os

import pandas as pd

from audio_utils import MIN_VALID_CLIP_BYTES, probe_audio_duration
from explorer.config import PROJECT_ROOT


def resolve_audio_path(path_value) -> str | None:
    """Resolve the exact clip path stored in CSV. No basename guessing."""
    if pd.isna(path_value) or not str(path_value).strip():
        return None

    raw_path = str(path_value).strip().replace("\\", os.sep)
    if os.path.isabs(raw_path):
        candidate = raw_path
    else:
        candidate = os.path.normpath(os.path.join(str(PROJECT_ROOT), raw_path))

    if os.path.exists(candidate) and os.path.isfile(candidate):
        return candidate
    return None


def describe_audio_issue(path: str) -> str | None:
    """Return a user-facing reason when a clip file exists but is not playable."""
    if not os.path.exists(path):
        return "Clip file is missing on disk. Re-run extract_clips.py."

    size = os.path.getsize(path)
    if size < MIN_VALID_CLIP_BYTES:
        return (
            f"Clip file is invalid ({size} bytes). "
            "The timestamp is likely outside the downloaded source audio duration."
        )

    duration = probe_audio_duration(path)
    if duration is None or duration < 0.1:
        return (
            "Clip file exists but is not valid audio. "
            "The timestamp may be beyond the downloaded source length."
        )
    return None
