"""
Rate limiter middleware — token bucket per IP.
Free tier: 30 req/min. API key holders: 300 req/min.
"""
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

class RateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, free_rate=30, free_period=60, paid_rate=300, paid_period=60):
        super().__init__(app)
        self.free_rate = free_rate
        self.free_period = free_period
        self.paid_rate = paid_rate
        self.paid_period = paid_period
        # {ip: {"tokens": float, "last": float, "is_paid": bool}}
        self.buckets = defaultdict(lambda: {"tokens": 30, "last": time.time(), "is_paid": False, "api_key": None})

    def _get_bucket(self, ip, api_key=None):
        now = time.time()
        b = self.buckets[ip]
        if api_key:
            b["is_paid"] = True
            b["api_key"] = api_key
        rate = self.paid_rate if b["is_paid"] else self.free_rate
        period = self.paid_period if b["is_paid"] else self.free_period
        elapsed = now - b["last"]
        b["tokens"] = min(rate, b["tokens"] + elapsed * (rate / period))
        b["last"] = now
        return b, rate

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Skip rate limiting for admin, health, docs, landing
        if path.startswith("/admin") or path.startswith("/health") or path == "/" or path == "/docs" or path == "/openapi.json" or path.startswith("/favicon") or path.startswith("/.well-known") or path.startswith("/robots.txt"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("x-api-key") or request.query_params.get("api_key")
        
        bucket, rate = self._get_bucket(ip, api_key)
        
        if bucket["tokens"] < 1:
            return JSONResponse(
                {"error": "Rate limit exceeded", "limit": f"{rate} req/min", "retry_after": 2},
                status_code=429,
                headers={"Retry-After": "2", "X-RateLimit-Limit": str(rate), "X-RateLimit-Remaining": "0"}
            )
        
        bucket["tokens"] -= 1
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))
        return response
