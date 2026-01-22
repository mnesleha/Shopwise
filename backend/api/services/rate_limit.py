from __future__ import annotations

from django.core.cache import cache


def rate_limit_hit(*, key: str, limit: int, window_s: int) -> bool:
    """Return True if the key is rate-limited (i.e., limit exceeded).

    Uses Django cache for a lightweight best-effort throttle.
    """
    if limit <= 0 or window_s <= 0:
        return False

    # First hit creates the counter with TTL.
    added = cache.add(key, 1, timeout=window_s)
    if added:
        return False

    try:
        current = cache.incr(key)
    except Exception:
        # If incr is unsupported for the cache backend, fall back to get/set.
        current = (cache.get(key) or 0) + 1
        cache.set(key, current, timeout=window_s)

    return int(current) > int(limit)
