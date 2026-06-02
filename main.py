"""
x402 Crypto Intelligence API
Zero-capital passive income — AI agents pay per request in USDC on Base
Data source: CoinGecko free API
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig, PaymentOption
from x402.http import FacilitatorConfig, HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer
from cdp_facilitator import CDPSupportedHTTPFacilitatorClient
import httpx
import time
import os
import logging
import base64

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("x402-crypto")

# --- Config ---
PAY_TO = os.environ.get("PAY_TO", "0xeb350f1692b16c8b7b02c66dedb76d018f6a9662")
PORT = int(os.environ.get("PORT", "4020"))
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Read CDP API keys from files
CDP_KEY_FILE = os.path.join(os.path.dirname(__file__), ".cdp_key")
CDP_SECRET_FILE = os.path.join(os.path.dirname(__file__), ".cdp_secret")
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

def _read_file(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except:
        return ""

cdp_key_id = os.environ.get("CDP_API_KEY_ID") or _read_file(CDP_KEY_FILE)
cdp_key_secret = os.environ.get("CDP_API_KEY_SECRET") or _read_file(CDP_SECRET_FILE)
NETWORK = os.environ.get("NETWORK") or _read_file(ENV_FILE).replace("NETWORK=", "").strip() or "eip155:8453"

# --- App ---
app = FastAPI(
    title="x402 Crypto Intelligence API",
    description="AI agent crypto data API — pay per request in USDC on Base. No API keys needed.",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- x402 Setup ---
class CDPAuthProvider:
    """CDP API key authentication using Ed25519 JWT."""
    def __init__(self, key_id: str, key_secret: str):
        self.key_id = key_id
        from cryptography.hazmat.primitives.asymmetric import ed25519
        raw = base64.b64decode(key_secret)
        self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw[:32])

    def _generate_jwt(self, method: str, host: str, path: str) -> str:
        import jwt as pyjwt
        now = int(time.time())
        payload = {
            "sub": self.key_id,
            "iss": "cdp",
            "aud": ["cdp_service"],
            "nbf": now,
            "exp": now + 120,
            "uri": f"{method} {host}{path}",
        }
        return pyjwt.encode(payload, self._private_key, algorithm="EdDSA", headers={"typ": "JWT", "kid": self.key_id})

    def get_auth_headers(self):
        from x402.http.facilitator_client_base import AuthHeaders
        host = "api.cdp.coinbase.com"
        token = self._generate_jwt("GET", host, "/platform/v2/x402/supported")
        headers = {"Authorization": f"Bearer {token}"}
        return AuthHeaders(
            verify=headers.copy(),
            settle=headers.copy(),
            supported=headers.copy(),
            bazaar=headers.copy(),
        )

if cdp_key_id and cdp_key_secret:
    # Production: CDP facilitator with JWT auth (Ed25519)
    auth = CDPAuthProvider(cdp_key_id, cdp_key_secret)
    facilitator = CDPSupportedHTTPFacilitatorClient(
        FacilitatorConfig(url="https://api.cdp.coinbase.com/platform/v2/x402", auth_provider=auth)
    )
    log.info(f"Using CDP facilitator (production), network: {NETWORK}")
else:
    # Testnet fallback: x402.org (no auth needed)
    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url="https://x402.org/facilitator")
    )
    log.info(f"Using x402.org facilitator (testnet), network: {NETWORK}")
server = x402ResourceServer(facilitator)
server.register(NETWORK, ExactEvmServerScheme())

routes = {
    "GET /api/v1/price/:coin_id": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Token price & 24h market data (BTC, ETH, SOL, etc)",
        mime_type="application/json",

        extensions={
            "bazaar": {
                "discoverable": True,
                "category": "crypto-data",
            }
        },
    ),
    "GET /api/v1/trending": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Currently trending crypto tokens",
        mime_type="application/json",

        extensions={
            "bazaar": {
                "discoverable": True,
                "category": "crypto-data",
            }
        },
    ),
    "GET /api/v1/market": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Global crypto market overview (total mcap, volume, BTC dominance)",
        mime_type="application/json",

        extensions={
            "bazaar": {
                "discoverable": True,
                "category": "crypto-data",
            }
        },
    ),
    "GET /api/v1/top-coins": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Top N coins by market cap with full data",
        mime_type="application/json",

        extensions={
            "bazaar": {
                "discoverable": True,
                "category": "crypto-data",
            }
        },
    ),
    "GET /api/v1/search": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Search coins by name or symbol",
        mime_type="application/json",

        extensions={
            "bazaar": {
                "discoverable": True,
                "category": "crypto-data",
            }
        },
    ),
    "GET /api/v1/defi": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Top DeFi protocols by TVL",
        mime_type="application/json",

        extensions={
            "bazaar": {
                "discoverable": True,
                "category": "crypto-data",
            }
        },
    ),
    "GET /api/v1/fear-greed": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Crypto Fear & Greed Index (current + history)",
        mime_type="application/json",

        extensions={
            "bazaar": {
                "discoverable": True,
                "category": "crypto-data",
            }
        },
    ),
    "GET /api/v1/gas": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Multi-chain gas price estimates",
        mime_type="application/json",
    ),
}

app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

# --- HTTP Client ---
client = httpx.AsyncClient(timeout=15.0, headers={"accept": "application/json"})
_last_cg_call = 0.0

async def cg_get(path: str, params: dict = None):
    global _last_cg_call
    now = time.time()
    wait = 6.5 - (now - _last_cg_call)
    if wait > 0:
        import asyncio
        await asyncio.sleep(wait)
    _last_cg_call = time.time()
    url = f"{COINGECKO_BASE}{path}"
    r = await client.get(url, params=params or {})
    if r.status_code == 429:
        import asyncio
        await asyncio.sleep(30)
        r = await client.get(url, params=params or {})
    r.raise_for_status()
    return r.json()


# === FREE ENDPOINTS ===
@app.get("/")
async def root():
    return {
        "service": "x402 Crypto Intelligence API",
        "version": "1.0.0",
        "payment": "USDC on Base (x402 protocol)",
        "pay_to": PAY_TO,
        "network": NETWORK,
        "endpoints": {
            "GET /api/v1/price/:coin_id": "$0.003 — Token price & market data",
            "GET /api/v1/trending": "$0.005 — Trending tokens",
            "GET /api/v1/market": "$0.003 — Global market overview",
            "GET /api/v1/top-coins": "$0.005 — Top coins by mcap",
            "GET /api/v1/search?q=": "$0.002 — Search coins",
            "GET /api/v1/defi": "$0.005 — DeFi protocols by TVL",
            "GET /api/v1/fear-greed": "$0.002 — Fear & Greed Index",
            "GET /api/v1/gas": "$0.002 — Multi-chain gas prices",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


# === PAID ENDPOINTS ===
@app.get("/api/v1/price/{coin_id}")
async def get_price(coin_id: str):
    data = await cg_get("/simple/price", {
        "ids": coin_id.lower(),
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
        "include_last_updated_at": "true",
    })
    if coin_id.lower() not in data:
        return {"error": f"Coin '{coin_id}' not found", "hint": "Use lowercase, e.g. 'bitcoin', 'ethereum', 'solana'"}
    info = data[coin_id.lower()]
    return {
        "coin": coin_id.lower(),
        "currency": "usd",
        "price": info.get("usd"),
        "market_cap": info.get("usd_market_cap"),
        "volume_24h": info.get("usd_24h_vol"),
        "change_24h_pct": info.get("usd_24h_change"),
        "last_updated": info.get("last_updated_at"),
    }


@app.get("/api/v1/trending")
async def get_trending():
    data = await cg_get("/search/trending")
    coins = []
    for item in data.get("coins", [])[:10]:
        c = item.get("item", {})
        coins.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "market_cap_rank": c.get("market_cap_rank"),
            "score": c.get("score"),
        })
    return {"trending": coins, "count": len(coins)}


@app.get("/api/v1/market")
async def get_market_overview():
    data = await cg_get("/global")
    gd = data.get("data", {})
    return {
        "total_market_cap_usd": gd.get("total_market_cap", {}).get("usd"),
        "total_volume_24h_usd": gd.get("total_volume", {}).get("usd"),
        "btc_dominance_pct": gd.get("market_cap_percentage", {}).get("btc"),
        "eth_dominance_pct": gd.get("market_cap_percentage", {}).get("eth"),
        "active_cryptos": gd.get("active_cryptocurrencies"),
        "total_markets": gd.get("markets"),
        "market_cap_change_24h_pct": gd.get("market_cap_change_percentage_24h_usd"),
    }


@app.get("/api/v1/top-coins")
async def get_top_coins(limit: int = Query(default=20, le=100)):
    data = await cg_get("/coins/markets", {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": str(min(limit, 100)),
        "page": "1",
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d",
    })
    coins = []
    for c in data:
        coins.append({
            "id": c.get("id"),
            "symbol": c.get("symbol"),
            "name": c.get("name"),
            "price": c.get("current_price"),
            "market_cap": c.get("market_cap"),
            "volume_24h": c.get("total_volume"),
            "change_1h": c.get("price_change_percentage_1h_in_currency"),
            "change_24h": c.get("price_change_percentage_24h_in_currency"),
            "change_7d": c.get("price_change_percentage_7d_in_currency"),
            "rank": c.get("market_cap_rank"),
        })
    return {"coins": coins, "count": len(coins)}


@app.get("/api/v1/search")
async def search_coins(q: str = Query(..., min_length=1)):
    data = await cg_get("/search", {"query": q})
    results = []
    for c in data.get("coins", [])[:10]:
        results.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "market_cap_rank": c.get("market_cap_rank"),
        })
    return {"query": q, "results": results, "count": len(results)}


@app.get("/api/v1/defi")
async def get_defi():
    data = await cg_get("/global/decentralized_finance_defi")
    return {
        "defi_market_cap_usd": data.get("defi_market_cap"),
        "eth_market_cap_usd": data.get("eth_market_cap"),
        "trading_volume_24h_usd": data.get("trading_volume_24h"),
        "defi_to_defi_ratio": data.get("defi_to_defi"),
        "top_coins_count": len(data.get("top_100_defi_coins", [])),
        "top_defi": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "symbol": c.get("symbol"),
                "price": c.get("price_btc"),
                "change_24h": c.get("price_change_percentage_24h"),
            }
            for c in data.get("top_100_defi_coins", [])[:15]
        ],
    }


@app.get("/api/v1/fear-greed")
async def get_fear_greed():
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get("https://api.alternative.me/fng/?limit=7&format=json")
        r.raise_for_status()
        data = r.json()
    entries = data.get("data", [])
    current = entries[0] if entries else {}
    return {
        "value": int(current.get("value", 0)),
        "classification": current.get("value_classification"),
        "history": [
            {"date": e.get("timestamp"), "value": int(e.get("value", 0)), "label": e.get("value_classification")}
            for e in entries
        ],
    }


@app.get("/api/v1/gas")
async def get_gas():
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get("https://api.etherscan.io/api?module=gastracker&action=gasoracle")
        eth_gas = {}
        if r.status_code == 200:
            result = r.json().get("result", {})
            eth_gas = {
                "low": result.get("SafeGasPrice"),
                "standard": result.get("ProposeGasPrice"),
                "fast": result.get("FastGasPrice"),
            }
    return {
        "ethereum": eth_gas,
        "note": "Gas prices in Gwei. Other chains (Base, Polygon, BSC) are L2/Low-cost.",
        "base_estimate_usd": 0.001,
        "polygon_estimate_usd": 0.0001,
    }


if __name__ == "__main__":
    import uvicorn
    log.info(f"Starting x402 Crypto API on port {PORT}, paying to {PAY_TO}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
