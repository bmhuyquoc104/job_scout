"""A tiny in-memory rate limiter: at most one allowed call per key every `interval` seconds."""

import time


class RateLimiter:
    # shortcut: in memory (resets on restart, per worker); use a shared store if scaled out.
    def __init__(self, interval: float | None = None) -> None:
        self._interval = interval
        self._last: dict[str, float] = {}

    def allow(self, key: str = "", interval: float | None = None) -> bool:
        """True and records the call if `key` is outside its interval; False otherwise."""
        wait = interval if interval is not None else self._interval or 0
        now = time.monotonic()
        if now - self._last.get(key, float("-inf")) < wait:
            return False
        self._last[key] = now
        return True
