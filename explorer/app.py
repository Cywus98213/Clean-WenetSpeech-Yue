from __future__ import annotations

import streamlit as st

from explorer.config import CLIP_CSV, CLIPS_DIR, PAGE_TITLE
from explorer.data import load_clip_data, load_download_failures
from explorer.views import render_clip_tab, render_failed_download_tab, render_metrics


def run() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")

    if not CLIP_CSV.parent.exists():
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    clip_df = load_clip_data()
    download_failed_df = load_download_failures()

    if clip_df.empty and download_failed_df.empty:
        st.warning("No CSV output found yet. Run the downloader and extractor first.")
        st.stop()

    st.title(PAGE_TITLE)
    st.caption("Downloader writes success/failed CSVs. Extract clips writes clip_view.csv.")
    render_metrics(clip_df, download_failed_df)

    clip_tab, failed_download_tab = st.tabs(["Clipped audio", "Failed downloads"])
    with clip_tab:
        render_clip_tab(clip_df)
    with failed_download_tab:
        render_failed_download_tab(download_failed_df)
