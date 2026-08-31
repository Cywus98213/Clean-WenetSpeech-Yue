"""Backward-compatible entry point for the Streamlit explorer."""

from explorer.bootstrap import configure_runtime

configure_runtime()

from explorer.app import run

run()
