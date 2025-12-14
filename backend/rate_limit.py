"""Simple in-memory rate limiting for worker readings."""

from __future__ import annotations

import time
from collections import defaultdict

import config

window_counts = defaultdict(list)


def allow(worker_id: str) -> bool:
    now = time.time()
    window = 1.0
    window_counts[worker_id] = [t for t in window_counts[worker_id] if now - t < window]
    if len(window_counts[worker_id]) >= config.RATE_LIMIT_READINGS_PER_SEC:
        return False
    window_counts[worker_id].append(now)
    return True


