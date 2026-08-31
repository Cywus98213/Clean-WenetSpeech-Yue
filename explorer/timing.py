from __future__ import annotations

import pandas as pd
import streamlit as st

from audio_utils import parse_time_stamp


def format_clip_timing(time_stamp, duration=None) -> dict[str, str] | None:
    """Return human-readable start minute/time and clip duration for verification."""
    start, end = parse_time_stamp(
        None if pd.isna(time_stamp) else str(time_stamp),
        None if duration is None or (isinstance(duration, float) and pd.isna(duration)) else duration,
    )
    if start is None or end is None:
        return None

    clip_duration = end - start
    start_minutes = int(start // 60)
    start_seconds = start % 60

    return {
        "raw": f"{start:.3f}s - {end:.3f}s",
        "start_label": f"{start_minutes} min {start_seconds:.3f} sec",
        "start_clock": f"{start_minutes}:{start_seconds:06.3f}",
        "duration_seconds": f"{clip_duration:.3f}s",
        "duration_mmss": f"{int(clip_duration // 60)}:{clip_duration % 60:06.3f}",
    }


def render_timing_block(row) -> None:
    timing = format_clip_timing(row.get("time_stamp"), row.get("duration"))
    if timing is None:
        st.write("**Clip timing**")
        st.warning("Could not parse time_stamp / duration for this row.")
        if row.get("time_stamp") is not None and not pd.isna(row.get("time_stamp")):
            st.caption(f"Raw time_stamp: {row.get('time_stamp')}")
        return

    st.write("**Clip timing (for verification)**")
    st.write(f"Starts at **{timing['start_label']}** ({timing['start_clock']})")
    st.write(f"Clip length: **{timing['duration_seconds']}** ({timing['duration_mmss']})")
    st.caption(f"Raw range: {timing['raw']}")
