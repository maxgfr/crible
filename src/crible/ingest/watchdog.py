"""ADR-0004 — a hard wall-clock watchdog for one upstream fetch.

yfinance pulls are known to hang indefinitely; a single stuck call must never
freeze the rolling ingest. The work runs on a daemon thread we abandon past
``timeout`` — Python can't kill the thread, but the loop moves on and the
socket-timed httpx client lets it die on its own. The callable's own exception
(incl. RateLimitedError) is re-raised on the caller thread so the caller's
error handling — backoff, skip, reschedule — still applies.
"""

from __future__ import annotations

import threading
from typing import Callable, TypeVar

T = TypeVar("T")


def call_with_timeout(func: Callable[[], T], timeout: float, label: str = "fetch") -> T:
    """Run ``func()`` under a hard wall-clock timeout. Raises ``TimeoutError``
    if it does not finish in time; otherwise returns its value or re-raises its
    exception."""
    box: dict[str, object] = {}

    def worker() -> None:
        try:
            box["result"] = func()
        except BaseException as exc:  # noqa: BLE001 — re-raised on the caller thread
            box["error"] = exc

    thread = threading.Thread(target=worker, name=label, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"{label} exceeded {timeout:.0f}s watchdog")
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box["result"]  # type: ignore[return-value]
