"""Token-bucket rate limiter for API clients."""

import threading
import time


class RateLimiter:
    """Thread-safe token-bucket rate limiter.

    Args:
        calls_per_window: Maximum calls allowed per window.
        window_seconds: Window duration in seconds.
    """

    def __init__(self, calls_per_window: int, window_seconds: float):
        self.calls_per_window = calls_per_window
        self.window_seconds = window_seconds
        self._tokens = calls_per_window
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
            # Sleep a fraction of the window before retrying
            time.sleep(self.window_seconds / self.calls_per_window)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * (self.calls_per_window / self.window_seconds)
        if new_tokens > 0:
            self._tokens = min(self.calls_per_window, self._tokens + new_tokens)
            self._last_refill = now
