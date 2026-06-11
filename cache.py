"""
In-memory response cache with TTL.
Reduces upstream API calls → faster responses for requesters.
"""
import time
import hashlib
import json
from typing import Any, Optional
from functools import wraps
import asyncio

class ResponseCache:
    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}
        self._hits = 0
        self._misses = 0

    def _key(self, prefix: str, args: tuple, kwargs: dict) -> str:
        raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            expires, data = self._store[key]
            if time.time() < expires:
                self._hits += 1
                return data
            else:
                del self._store[key]
        self._misses += 1
        return None

    def set(self, key: str, data: Any, ttl: int):
        self._store[key] = (time.time() + ttl, data)

    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
            "entries": len(self._store),
        }

    def cleanup(self):
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, (exp, _) in self._store.items() if now >= exp]
        for k in expired:
            del self._store[k]


cache = ResponseCache()


def cached(ttl: int, prefix: str = ""):
    """Decorator: cache async function result for `ttl` seconds."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache._key(prefix or func.__name__, args, kwargs)
            hit = cache.get(key)
            if hit is not None:
                return hit
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator


# TTL presets (seconds)
TTL_PRICE = 60        # Prices change fast
TTL_TRENDING = 300    # Trending changes every few minutes
TTL_MARKET = 120      # Market overview
TTL_DEFI = 600        # DeFi protocols change slowly
TTL_CHAINS = 1800     # Chains change rarely
TTL_GAS = 30          # Gas prices change fast
TTL_WALLET = 15       # Wallet balance needs fresh data
TTL_DEX = 60          # DEX pairs
TTL_SEARCH = 120      # Search results


# Background cleanup every 5 minutes
async def _cleanup_loop():
    while True:
        await asyncio.sleep(300)
        cache.cleanup()
