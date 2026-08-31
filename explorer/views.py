from __future__ import annotations

import pandas as pd
import streamlit as st

from explorer.audio_paths import describe_audio_issue, resolve_audio_path
from explorer.timing import render_timing_block


def render_metrics(clip_df: pd.DataFrame, failed_df: pd.DataFrame) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Clip rows", len(clip_df))
    col2.metric("Failed downloads", len(failed_df))
    col3.metric(
        "Audio files found",
        sum(
            1
            for path in clip_df.get("local_audio_path", pd.Series(dtype=str)).fillna("")
            if resolve_audio_path(path)
        ),
    )


def render_clip_tab(clip_df: pd.DataFrame) -> None:
    if clip_df.empty:
        st.info("No clips in clip_view.csv yet.")
        return

    st.subheader(f"Showing {len(clip_df)} clipped rows")
    st.dataframe(clip_df)
    st.write("---")

    for _, row in clip_df.iterrows():
        row_key = str(row.get("key", "no-key"))
        time_stamp = row.get("time_stamp", "")
        expander_label = f"{row.get('video_id', row_key)} | {time_stamp}"
        with st.expander(expander_label, expanded=False):
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.write("**Text**")
                st.write(row.get("rover_result", ""))
                render_timing_block(row)
                st.write("**Clip file**")
                st.code(row.get("local_audio_path", ""))
                st.write("**Link**")
                st.write(row.get("link", ""))
                st.write("**Region**")
                st.write(row.get("region", ""))
            with col_right:
                audio_path = resolve_audio_path(row.get("local_audio_path"))
                if audio_path:
                    issue = describe_audio_issue(audio_path)
                    if issue:
                        st.error(issue)
                    else:
                        st.success("Audio available")
                        st.audio(audio_path, format="audio/mp3")
                else:
                    st.warning("Clip file missing on disk. Re-run extract_clips.py for this row.")
                    st.caption(f"Expected: {row.get('local_audio_path', '')}")


def render_failed_download_tab(failed_df: pd.DataFrame) -> None:
    if failed_df.empty:
        st.info("No failed download rows in failed/failed_links.csv.")
        return

    st.subheader(f"Showing {len(failed_df)} failed download rows")
    display_df = failed_df.copy()
    if "error" in display_df.columns:
        failed_cols = [
            col
            for col in ["error", "key", "video_id", "link", "time_stamp", "region"]
            if col in display_df.columns
        ]
        rest_cols = [col for col in display_df.columns if col not in failed_cols]
        display_df = display_df[failed_cols + rest_cols]
    st.dataframe(display_df)
    st.write("---")

    for _, row in failed_df.iterrows():
        with st.expander(str(row.get("video_id", row.get("key", "failed-download"))), expanded=False):
            st.write("**Error**")
            st.error(row.get("error", "unknown"))
            render_timing_block(row)
            st.write("**Link**")
            st.write(row.get("link", ""))
