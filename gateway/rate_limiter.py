import threading
import time
from typing import Iterable

from .schemas import Message

# Token bucket for request-rate limiting: allows short bursts up to
# RATE_CAPACITY, refilling at RATE_REFILL_PER_SECOND afterward. Tunable
# knobs, not fixed law — see README Slice 6.
RATE_CAPACITY = 5
RATE_REFILL_PER_SECOND = 0.5  # 1 request per 2 seconds sustained

# Per-client cost budget over a rolling window. Real token counts aren't
# available without a real upstream LLM call (gateway/llm_client.py is
# still a stub) — character count is used as a documented stand-in.
DAILY_COST_BUDGET = 20_000
COST_WINDOW_SECONDS = 24 * 60 * 60

_clock = time.monotonic
_lock = threading.Lock()
_buckets: dict[str, tuple[float, float]] = {}  # client_id -> (tokens, last_refill)
_cost_usage: dict[str, tuple[float, float]] = {}  # client_id -> (used, window_start)


class RateLimitExceeded(Exception):
    def __init__(self, reason: str, retry_after: float):
        self.reason = reason
        self.retry_after = max(0.0, retry_after)
        super().__init__(f"rate limit exceeded: {reason}, retry after {self.retry_after:.1f}s")


def check_rate_limit(client_id: str) -> None:
    now = _clock()
    with _lock:
        tokens, last_refill = _buckets.get(client_id, (float(RATE_CAPACITY), now))
        tokens = min(RATE_CAPACITY, tokens + (now - last_refill) * RATE_REFILL_PER_SECOND)

        if tokens < 1:
            _buckets[client_id] = (tokens, now)
            raise RateLimitExceeded("request_rate", (1 - tokens) / RATE_REFILL_PER_SECOND)

        _buckets[client_id] = (tokens - 1, now)


def check_cost_budget(client_id: str, estimated_cost: int) -> None:
    now = _clock()
    with _lock:
        used, window_start = _cost_usage.get(client_id, (0.0, now))

        if now - window_start > COST_WINDOW_SECONDS:
            used, window_start = 0.0, now

        if used + estimated_cost > DAILY_COST_BUDGET:
            _cost_usage[client_id] = (used, window_start)
            raise RateLimitExceeded("cost_budget", COST_WINDOW_SECONDS - (now - window_start))

        _cost_usage[client_id] = (used + estimated_cost, window_start)


def estimate_cost(messages: Iterable[Message]) -> int:
    # Character count as a stand-in for token count — see README Slice 6.
    return sum(len(message.content) for message in messages)
