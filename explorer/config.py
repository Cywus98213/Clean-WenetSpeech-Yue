from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLIP_CSV = PROJECT_ROOT / "speech_clips" / "clip_view.csv"
FAILED_CSV = PROJECT_ROOT / "failed" / "failed_links.csv"
CLIPS_DIR = PROJECT_ROOT / "speech_clips"

PAGE_TITLE = "WenetSpeech-Yue Explorer"
