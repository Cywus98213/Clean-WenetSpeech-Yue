from __future__ import annotations

import asyncio
import sys


def configure_runtime() -> None:
    """Apply Windows-friendly asyncio settings before Streamlit starts."""
    if sys.platform != "win32":
        return

    # On Windows, Streamlit/Tornado can log harmless ConnectionResetError noise
    # when the browser refreshes or closes the websocket. Selector policy often
    # reduces these messages on Python 3.11/3.12.
    policy_cls = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy_cls is not None:
        asyncio.set_event_loop_policy(policy_cls())
