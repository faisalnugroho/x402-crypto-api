"""
x402 Crypto Intelligence API v3.0
Zero-capital passive income — AI agents pay per request in USDC on Base
Data sources: CoinGecko, DexScreener, DefiLlama, Etherscan, Public RPCs
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig, PaymentOption
from x402.http import FacilitatorConfig, HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer
from x402.extensions.bazaar import declare_discovery_extension, OutputConfig
from cdp_facilitator import CDPSupportedHTTPFacilitatorClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
import httpx
import time
import os
import logging
import base64
import json
import tracker
from endpoints import router as v2_router
from premium_endpoints import router as premium_router
from cache import cached, cache, TTL_PRICE, TTL_TRENDING, TTL_MARKET, TTL_DEFI, _cleanup_loop
from etherscan_endpoints import router as etherscan_router
from ai_endpoints import router as ai_router
from rate_limiter import RateLimiter

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("x402-crypto")

# --- Config ---
PAY_TO = os.environ.get("PAY_TO", "0xeb350f1692b16c8b7b02c66dedb76d018f6a9662")
PORT = int(os.environ.get("PORT", "4020"))
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
# Public base URL for discovery metadata. Set PUBLIC_URL env to override.
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://civilization-jacket-released-desperate.trycloudflare.com")

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

# Builder Code (ERC-8021) — declares seller app code in 402 responses.
# This is the "a" field in the x402 builder-code extension. Buyers will
# auto-echo this back at payment time; the CDP facilitator CBOR-encodes
# {a, s, w} into an ERC-8021 Schema 2 calldata suffix at settlement.
BUILDER_CODE_APP = "bc_1g4yopsy"

# --- App ---
app = FastAPI(
    title="x402 Crypto Intelligence API",
    description="AI agent crypto data API + AI micro-SaaS — pay per request in USDC on Base. No API keys needed.",
    version="4.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter (before payment middleware)
app.add_middleware(RateLimiter, free_rate=30, paid_rate=300)

# Mount routers
app.include_router(v2_router)
app.include_router(premium_router)
app.include_router(etherscan_router)
app.include_router(ai_router)

# --- x402 Setup ---
class CDPAuthProvider:
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
        base = "/platform/v2/x402"
        def hdr(method: str, path: str) -> dict:
            return {"Authorization": f"Bearer {self._generate_jwt(method, host, path)}"}
        return AuthHeaders(
            verify=hdr("POST", base + "/verify"),
            settle=hdr("POST", base + "/settle"),
            supported=hdr("GET", base + "/supported"),
            bazaar=hdr("GET", base + "/bazaar"),
        )

if cdp_key_id and cdp_key_secret:
    auth = CDPAuthProvider(cdp_key_id, cdp_key_secret)
    facilitator = CDPSupportedHTTPFacilitatorClient(
        FacilitatorConfig(url="https://api.cdp.coinbase.com/platform/v2/x402", auth_provider=auth)
    )
    log.info(f"Using CDP facilitator (production), network: {NETWORK}")
else:
    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url="https://x402.org/facilitator")
    )
    log.info(f"Using x402.org facilitator (testnet), network: {NETWORK}")
server = x402ResourceServer(facilitator)
server.register(NETWORK, ExactEvmServerScheme())

# --- Bazaar discovery helper (CDP Bazaar indexing) ---
BC = {"builder-code": {"info": {"a": "bc_1g4yopsy"}}}

def bz(category, **kw):
    """Merge declare_discovery_extension output with builder-code extension."""
    ext = declare_discovery_extension(**kw)
    ext["bazaar"]["category"] = category
    ext.update(BC)
    return ext



routes = {
    # CoinGecko
    "GET /api/v1/price/:coin_id": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Token price & 24h market data (BTC, ETH, SOL, etc)",
        mime_type="application/json",
        extensions=bz("crypto-data",
        path_params_schema={"properties": {"coin_id": {"type": "string", "description": "CoinGecko coin id, e.g. bitcoin, ethereum, solana"}}, "required": ["coin_id"]},
        output=OutputConfig(example={"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "price_usd": 115000.5, "market_cap": 2280000000000, "volume_24h": 45000000000, "change_24h_pct": 2.14})),
    ),
    "GET /api/v1/trending": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Currently trending crypto tokens",
        mime_type="application/json",
        extensions=bz("crypto-data",
        output=OutputConfig(example={"coins": [{"id": "bitcoin", "symbol": "BTC", "rank": 1, "price_btc": 1.0}]})),
    ),
    "GET /api/v1/market": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Global crypto market overview",
        mime_type="application/json",
        extensions=bz("crypto-data",
        output=OutputConfig(example={"total_market_cap_usd": 3900000000000, "total_volume_24h_usd": 180000000000, "btc_dominance_pct": 54.2, "active_cryptocurrencies": 14000})),
    ),
    "GET /api/v1/top-coins": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Top N coins by market cap",
        mime_type="application/json",
        extensions=bz("crypto-data",
        input={"limit": "20"},
        input_schema={"properties": {"limit": {"type": "integer", "description": "Number of coins to return (default 20, max 250)"}}, "required": []},
        output=OutputConfig(example=[{"id": "bitcoin", "symbol": "btc", "price_usd": 115000, "market_cap": 2280000000000, "change_24h_pct": 2.1}])),
    ),
    "GET /api/v1/search": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Search coins by name or symbol",
        mime_type="application/json",
        extensions=bz("crypto-data",
        input={"q": "bitcoin"},
        input_schema={"properties": {"q": {"type": "string", "description": "Search query — coin name or symbol"}}, "required": ["q"]},
        output=OutputConfig(example={"coins": [{"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "market_cap_rank": 1}]})),
    ),
    "GET /api/v1/defi": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Top DeFi protocols by TVL",
        mime_type="application/json",
        extensions=bz("crypto-data",
        output=OutputConfig(example={"defi_market_cap_usd": 120000000000, "eth_staked_usd": 55000000000, "top_protocols": [{"name": "Lido", "tvl_usd": 30000000000}]})),
    ),
    "GET /api/v1/fear-greed": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Crypto Fear & Greed Index",
        mime_type="application/json",
        extensions=bz("crypto-data",
        output=OutputConfig(example={"value": 72, "label": "Greed", "timestamp": "2026-08-22"})),
    ),
    "GET /api/v1/gas": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Multi-chain gas price estimates",
        mime_type="application/json",
        extensions=bz("chain-data",
            output=OutputConfig(example={"ethereum": {"gwei": 12.5}, "base": {"gwei": 0.01}, "polygon": {"gwei": 30.2}})),
    ),
    # DEX
    "GET /api/v1/dex/token/:chain/:address": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="All DEX trading pairs for a token",
        mime_type="application/json",
        extensions=bz("dex-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, solana, bsc, arbitrum, polygon"}, "address": {"type": "string", "description": "Token contract address"}}, "required": ["chain", "address"]},
        output=OutputConfig(example={"pairs": [{"chainId": "ethereum", "dexId": "uniswap", "pairAddress": "0x...", "priceUsd": "115000", "volume24h": 1200000}]})),
    ),
    "GET /api/v1/dex/pair/:chain/:pair_id": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Detailed DEX pair info",
        mime_type="application/json",
        extensions=bz("dex-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, solana, bsc"}, "pair_id": {"type": "string", "description": "DEX pair/liquidity pool address"}}, "required": ["chain", "pair_id"]},
        output=OutputConfig(example={"chainId": "ethereum", "pairAddress": "0x...", "priceUsd": "115000", "liquidityUsd": 5000000, "volume24h": 1200000})),
    ),
    "GET /api/v1/dex/search": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Search DEX tokens",
        mime_type="application/json",
        extensions=bz("dex-data",
        input={"q": "pepe"},
        input_schema={"properties": {"q": {"type": "string", "description": "Token name or symbol to search on DEX"}}, "required": ["q"]},
        output=OutputConfig(example={"tokens": [{"chainId": "ethereum", "address": "0x...", "name": "Pepe", "symbol": "PEPE", "priceUsd": "0.00001"}]})),
    ),
    "GET /api/v1/dex/trending": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Trending tokens on DEX",
        mime_type="application/json",
        extensions=bz("dex-data",
        output=OutputConfig(example={"tokens": [{"chainId": "base", "address": "0x...", "symbol": "TOKEN", "priceUsd": "0.05", "volume24h": 500000}]})),
    ),
    "GET /api/v1/dex/boosted": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Top boosted tokens on DEX",
        mime_type="application/json",
        extensions=bz("dex-data",
        output=OutputConfig(example={"tokens": [{"chainId": "base", "address": "0x...", "symbol": "TOKEN", "boostAmount": 100}]})),
    ),
    # DeFiLlama
    "GET /api/v1/protocols": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="All DeFi protocols with TVL",
        mime_type="application/json",
        extensions=bz("defi-data",
        output=OutputConfig(example=[{"name": "Lido", "symbol": "LDO", "tvl_usd": 30000000000, "chain": "Ethereum", "category": "Liquid Staking"}])),
    ),
    "GET /api/v1/tvl/:protocol": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Protocol TVL history",
        mime_type="application/json",
        extensions=bz("defi-data",
        path_params_schema={"properties": {"protocol": {"type": "string", "description": "DefiLlama protocol slug, e.g. lido, aave, uniswap"}}, "required": ["protocol"]},
        output=OutputConfig(example={"protocol": "lido", "tvl_history": [{"date": "2026-08-01", "tvl_usd": 29500000000}]})),
    ),
    "GET /api/v1/chains": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="All supported blockchain chains",
        mime_type="application/json",
        extensions=bz("chain-data",
        output=OutputConfig(example=[{"name": "Ethereum", "tvl_usd": 60000000000}, {"name": "Base", "tvl_usd": 4000000000}])),
    ),
    # Wallet
    "GET /api/v1/wallet/:chain/:address": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="EVM wallet native balance + USD",
        mime_type="application/json",
        extensions=bz("wallet-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, bsc, polygon, arbitrum, optimism"}, "address": {"type": "string", "description": "EVM wallet address (0x...)"}}, "required": ["chain", "address"]},
        output=OutputConfig(example={"chain": "ethereum", "address": "0x...", "native_balance": "1.234", "native_usd": 4500.5})),
    ),
    "GET /api/v1/gas/multi": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Gas prices across 6 chains",
        mime_type="application/json",
        extensions=bz("chain-data",
        output=OutputConfig(example={"ethereum": 12.5, "base": 0.01, "polygon": 30.2, "arbitrum": 0.1, "optimism": 0.05, "bsc": 3.0})),
    ),
    # Etherscan
    "GET /api/v1/wallet/:chain/:address/transactions": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Wallet transaction history",
        mime_type="application/json",
        extensions=bz("wallet-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, bsc, polygon"}, "address": {"type": "string", "description": "EVM wallet address (0x...)"}}, "required": ["chain", "address"]},
        output=OutputConfig(example={"transactions": [{"hash": "0x...", "from": "0x...", "to": "0x...", "value_eth": "0.5", "timestamp": 1724300000}]})),
    ),
    "GET /api/v1/wallet/:chain/:address/tokens": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="ERC-20 token transfer history",
        mime_type="application/json",
        extensions=bz("wallet-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, bsc, polygon"}, "address": {"type": "string", "description": "EVM wallet address (0x...)"}}, "required": ["chain", "address"]},
        output=OutputConfig(example={"token_transfers": [{"token_symbol": "USDC", "value": "1000", "from": "0x...", "to": "0x...", "timestamp": 1724300000}]})),
    ),
    "GET /api/v1/wallet/:chain/:address/internal": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Internal transactions",
        mime_type="application/json",
        extensions=bz("wallet-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, bsc, polygon"}, "address": {"type": "string", "description": "EVM wallet address (0x...)"}}, "required": ["chain", "address"]},
        output=OutputConfig(example={"internal_txs": [{"hash": "0x...", "from": "0x...", "to": "0x...", "value_eth": "0.1"}]})),
    ),
    "GET /api/v1/contract/:chain/:address/abi": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Smart contract ABI + source",
        mime_type="application/json",
        extensions=bz("contract-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, bsc, polygon"}, "address": {"type": "string", "description": "Smart contract address (0x...)"}}, "required": ["chain", "address"]},
        output=OutputConfig(example={"contract_name": "USDC", "compiler": "v0.8.19", "verified": True, "abi": [{"type": "function", "name": "balanceOf"}]})),
    ),
    "GET /api/v1/token/:chain/:address/info": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="ERC-20 token info",
        mime_type="application/json",
        extensions=bz("token-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, bsc, polygon"}, "address": {"type": "string", "description": "ERC-20 token contract address (0x...)"}}, "required": ["chain", "address"]},
        output=OutputConfig(example={"name": "USD Coin", "symbol": "USDC", "decimals": 6, "total_supply": "35000000000"})),
    ),
    "GET /api/v1/gas/:chain": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Etherscan gas tracker",
        mime_type="application/json",
        extensions=bz("chain-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, bsc, polygon, arbitrum"}}, "required": ["chain"]},
        output=OutputConfig(example={"chain": "ethereum", "safe_gwei": 12.0, "standard_gwei": 13.5, "fast_gwei": 15.0})),
    ),
    "GET /api/v1/block/:chain/latest": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Latest block number",
        mime_type="application/json",
        extensions=bz("chain-data",
        path_params_schema={"properties": {"chain": {"type": "string", "description": "Chain slug: ethereum, base, bsc, polygon"}}, "required": ["chain"]},
        output=OutputConfig(example={"chain": "ethereum", "block_number": 21500000, "timestamp": 1724300000})),
    ),
    # Premium
    "GET /api/v1/whale/ethereum": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.010", network=NETWORK)],
        description="Whale alerts — large ETH transfers",
        mime_type="application/json",
        extensions=bz("premium",
        output=OutputConfig(example={"whale_transfers": [{"hash": "0x...", "from": "0x...", "to": "0x...", "value_eth": 5000, "usd_value": 17500000}]})),
    ),
    "GET /api/v1/sentiment": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Market sentiment (Fear & Greed + trending)",
        mime_type="application/json",
        extensions=bz("premium",
        output=OutputConfig(example={"fear_greed": {"value": 72, "label": "Greed"}, "trending": ["bitcoin", "solana"], "overall": "bullish"})),
    ),
    "GET /api/v1/screener": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="Token screener by mcap/volume/change",
        mime_type="application/json",
        extensions=bz("premium",
        input={"min_mcap": "100000000", "sort": "change_24h"},
        input_schema={"properties": {"min_mcap": {"type": "string", "description": "Minimum market cap in USD"}, "sort": {"type": "string", "description": "Sort field: change_24h, volume, mcap"}, "limit": {"type": "integer", "description": "Max results (default 20)"}}, "required": []},
        output=OutputConfig(example=[{"id": "solana", "symbol": "sol", "price_usd": 180, "change_24h_pct": 8.5, "volume_24h": 3000000000}])),
    ),
    "GET /api/v1/portfolio": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.008", network=NETWORK)],
        description="Multi-wallet portfolio tracker",
        mime_type="application/json",
        extensions=bz("premium",
        input={"wallets": "0xabc...,0xdef..."},
        input_schema={"properties": {"wallets": {"type": "string", "description": "Comma-separated EVM wallet addresses (up to 10)"}}, "required": ["wallets"]},
        output=OutputConfig(example={"wallets": [{"address": "0x...", "total_usd": 12500.5, "tokens": [{"symbol": "ETH", "usd": 4500}]}]})),
    ),
    "GET /api/v1/movers": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.003", network=NETWORK)],
        description="Top gainers & losers (24h)",
        mime_type="application/json",
        extensions=bz("premium",
        output=OutputConfig(example={"gainers": [{"id": "token-a", "change_24h_pct": 45.2}], "losers": [{"id": "token-b", "change_24h_pct": -30.1}]})),
    ),
    "GET /api/v1/prices": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.002", network=NETWORK)],
        description="Batch price lookup (up to 50 tokens)",
        mime_type="application/json",
        extensions=bz("premium",
        input={"ids": "bitcoin,ethereum,solana"},
        input_schema={"properties": {"ids": {"type": "string", "description": "Comma-separated CoinGecko coin ids (up to 50)"}}, "required": ["ids"]},
        output=OutputConfig(example={"bitcoin": {"usd": 115000}, "ethereum": {"usd": 4500}, "solana": {"usd": 180}})),
    ),
    # === AI Vertical Micro-SaaS (v4.0) ===
    "POST /api/v1/ai/legal-review": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.020", network=NETWORK)],
        description="AI legal contract review — risk analysis, key terms, red flags",
        mime_type="application/json",
        extensions=bz("ai-services",
        input={"contract_text": "This agreement is made between..."},
        input_schema={"properties": {"contract_text": {"type": "string", "description": "Full contract text to analyze (max 50k chars)"}}, "required": ["contract_text"]},
        body_type="json",
        output=OutputConfig(example={"risk_level": "medium", "red_flags": ["Unlimited liability clause"], "key_terms": ["Termination: 30 days notice"], "summary": "Standard service agreement with one high-risk clause"})),
    ),
    "POST /api/v1/ai/tax-id": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.015", network=NETWORK)],
        description="Indonesian PPh 21 tax estimator (UU HPP progressive brackets)",
        mime_type="application/json",
        extensions=bz("ai-services",
        input={"gross_income_idr": 120000000, "status": "TK0"},
        input_schema={"properties": {"gross_income_idr": {"type": "number", "description": "Annual gross income in IDR"}, "status": {"type": "string", "description": "Tax status: TK0, K0, K1, K2, K3"}}, "required": ["gross_income_idr"]},
        body_type="json",
        output=OutputConfig(example={"ptkp": 54000000, "pkp": 66000000, "pph21_annual": 3300000, "effective_rate_pct": 2.75})),
    ),
    "POST /api/v1/ai/invoice-ocr": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.010", network=NETWORK)],
        description="AI invoice/receipt parser — text to structured JSON",
        mime_type="application/json",
        extensions=bz("ai-services",
        input={"text": "INVOICE #12345 Total: $500.00 Due: 2026-09-01"},
        input_schema={"properties": {"text": {"type": "string", "description": "Raw invoice/receipt text to parse into structured JSON"}}, "required": ["text"]},
        body_type="json",
        output=OutputConfig(example={"invoice_number": "12345", "total": 500.0, "currency": "USD", "due_date": "2026-09-01", "vendor": "Acme Corp"})),
    ),
    "POST /api/v1/ai/sentiment": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to=PAY_TO, price="$0.005", network=NETWORK)],
        description="AI text sentiment + intent + entity extraction (multi-language)",
        mime_type="application/json",
        extensions=bz("ai-services",
        input={"text": "The product exceeded all expectations"},
        input_schema={"properties": {"text": {"type": "string", "description": "Text to analyze for sentiment, intent and entities (multi-language)"}}, "required": ["text"]},
        body_type="json",
        output=OutputConfig(example={"sentiment": "positive", "score": 0.92, "intent": "praise", "entities": [{"text": "product", "type": "noun"}], "language": "en"})),
    ),
}

app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)


# --- Tracking Middleware ---
class TrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/admin"):
            return await call_next(request)

        import uuid
        req_id = uuid.uuid4().hex[:12]
        request.state.req_id = req_id

        start = time.time()
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")
        endpoint = path

        paid = False
        payer = None
        amount = 0.0

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = int((time.time() - start) * 1000)
            tracker.log_request(endpoint, 500, ip=ip, user_agent=ua,
                                response_ms=elapsed, error=str(exc))
            raise

        elapsed = int((time.time() - start) * 1000)
        status = response.status_code

        if status == 200:
            # x402 v2 sends PAYMENT-SIGNATURE header (base64 JSON)
            payment_header = request.headers.get("payment-signature", "") or request.headers.get("x-payment", "")
            if payment_header:
                paid = True
                try:
                    import base64 as b64
                    decoded = b64.b64decode(payment_header)
                    pdata = json.loads(decoded)
                    # v2 structure: payload.authorization.from / .value
                    auth = pdata.get("payload", {}).get("authorization", {})
                    payer = auth.get("from")
                    raw_amount = auth.get("value", "0")
                    # USDC has 6 decimals
                    amount = float(raw_amount) / 1e6
                except Exception:
                    pass
                # Record revenue
                if payer and amount > 0:
                    tracker.log_payment(endpoint, payer, amount)

        tracker.log_request(endpoint, status, paid=paid, payer_address=payer,
                            amount_usdc=amount, response_ms=elapsed,
                            ip=ip, user_agent=ua)

        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{elapsed}ms"
        response.headers["X-Powered-By"] = "x402-crypto-api"

        return response

app.add_middleware(TrackingMiddleware)

# --- ShadowFeed HMAC ---
import hmac as hmac_mod
import hashlib

SHADOWFEED_SECRET = os.environ.get("SHADOWFEED_PARTNER_SECRET", "")

class ShadowFeedHMACMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        sf_signature = request.headers.get("x-shadowfeed-signature")
        sf_timestamp = request.headers.get("x-shadowfeed-timestamp")
        
        if sf_signature and SHADOWFEED_SECRET:
            try:
                ts = int(sf_timestamp)
                if abs(time.time() - ts) > 300:
                    return JSONResponse({"error": "Request expired"}, status_code=401)
            except (TypeError, ValueError):
                return JSONResponse({"error": "Invalid timestamp"}, status_code=401)
            
            body = b""
            if request.method in ("POST", "PUT"):
                body = await request.body()
            
            message = f"{sf_timestamp}.{request.method}.{request.url.path}".encode()
            if body:
                message += b"." + body
            
            expected = hmac_mod.new(
                SHADOWFEED_SECRET.encode(), message, hashlib.sha256
            ).hexdigest()
            
            if not hmac_mod.compare_digest(sf_signature, expected):
                return JSONResponse({"error": "Invalid HMAC signature"}, status_code=401)
        
        return await call_next(request)

if SHADOWFEED_SECRET:
    app.add_middleware(ShadowFeedHMACMiddleware)
    log.info("ShadowFeed HMAC verification enabled")

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


# === FREE ENDPOINTS (attract users) ===
@app.on_event("startup")
async def startup():
    import asyncio
    asyncio.create_task(_cleanup_loop())
    log.info("Cache cleanup loop started")


@app.get("/")
async def root():
    """Professional landing page."""
    return HTMLResponse(LANDING_HTML)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time(), "version": "4.0.0"}


@app.get("/robots.txt", response_class=HTMLResponse)
async def robots_txt():
    return "User-agent: *\nAllow: /\nAllow: /health\nAllow: /docs\nDisallow: /api/\nDisallow: /admin/\n"


@app.get("/.well-known/shadowfeed-feeds.json")
async def shadowfeed_manifest():
    manifest_path = os.path.join(os.path.dirname(__file__), "shadowfeed-manifest.json")
    try:
        with open(manifest_path) as f:
            return JSONResponse(json.load(f))
    except FileNotFoundError:
        return JSONResponse({"error": "Manifest not found"}, status_code=404)


@app.get("/llms.txt", response_class=HTMLResponse)
async def llms_txt():
    """llms.txt — LLM discovery file for AI agents."""
    base = PUBLIC_URL
    lines = [
        "# x402 Crypto Intelligence API",
        "",
        "> AI agent crypto data API — pay per request in USDC on Base via x402 protocol.",
        "> 35+ endpoints: prices, DEX, DeFi, Fear & Greed, whale alerts, wallet analytics, AI micro-SaaS.",
        "> No API keys, no signup. Payment is the authentication.",
        "",
        "## Payment",
        f"- Protocol: x402 v2 (HTTP 402 Payment Required)",
        "- Network: Base mainnet (eip155:8453)",
        "- Asset: USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)",
        f"- Pay to: {PAY_TO}",
        "- Price range: $0.002–$0.010 per request",
        "",
        "## Free Endpoints (no payment)",
        f"- GET {base}/api/v1/free/health — API health + cache stats",
        f"- GET {base}/api/v1/free/fear-greed — Fear & Greed Index (basic)",
        f"- GET {base}/api/v1/free/gas — ETH gas prices (basic)",
        f"- GET {base}/api/v1/free/price/{{coin_id}} — Price for top 20 coins",
        f"- GET {base}/api/v1/free/market — Global market overview (basic)",
        f"- GET {base}/api/v1/free/catalog — Full endpoint catalog",
        "",
        "## Paid Endpoints (x402)",
        f"- GET {base}/api/v1/price/{{coin_id}} — $0.003 — Token price & 24h market data",
        f"- GET {base}/api/v1/trending — $0.005 — Trending crypto tokens",
        f"- GET {base}/api/v1/market — $0.003 — Global crypto market overview",
        f"- GET {base}/api/v1/top-coins — $0.005 — Top N coins by market cap",
        f"- GET {base}/api/v1/search — $0.002 — Search coins by name/symbol",
        f"- GET {base}/api/v1/defi — $0.005 — Top DeFi protocols by TVL",
        f"- GET {base}/api/v1/fear-greed — $0.002 — Fear & Greed Index (full)",
        f"- GET {base}/api/v1/gas — $0.002 — Gas prices (multi-chain)",
        f"- GET {base}/api/v1/dex/token/{{chain}}/{{address}} — $0.003 — DEX token data",
        f"- GET {base}/api/v1/dex/pair/{{chain}}/{{pair_id}} — $0.003 — DEX pair data",
        f"- GET {base}/api/v1/dex/search — $0.002 — DEX search",
        f"- GET {base}/api/v1/dex/trending — $0.003 — DEX trending",
        f"- GET {base}/api/v1/protocols — $0.003 — DeFiLlama protocols",
        f"- GET {base}/api/v1/tvl/{{protocol}} — $0.002 — Protocol TVL",
        f"- GET {base}/api/v1/chains — $0.002 — Chain TVL rankings",
        f"- GET {base}/api/v1/wallet/{{chain}}/{{address}} — $0.005 — Wallet overview",
        f"- GET {base}/api/v1/whale/ethereum — $0.010 — Whale alerts (Ethereum)",
        f"- GET {base}/api/v1/sentiment — $0.005 — Full sentiment analysis",
        f"- GET {base}/api/v1/screener — $0.005 — Token screener",
        "",
        "## How to Pay",
        "1. Send GET request to any paid endpoint",
        "2. Receive HTTP 402 with `payment-required` header (base64 JSON)",
        "3. Sign payment authorization with your wallet (EIP-3009 transferWithAuthorization)",
        "4. Retry request with `PAYMENT-SIGNATURE` header",
        "5. Receive data + settlement receipt",
        "",
        "## Links",
        f"- Docs: {base}/docs",
        f"- OpenAPI: {base}/openapi.json",
        f"- Discovery: {base}/.well-known/x402.json",
        "- GitHub: https://github.com/faisalnugroho/x402-crypto-api",
    ]
    return "\n".join(lines)


@app.get("/.well-known/x402.json")
async def x402_discovery():
    """x402 discovery metadata for agent crawlers and directories."""
    base = PUBLIC_URL
    endpoints = []
    for route_key, cfg in routes.items():
        method, path = route_key.split(" ", 1)
        price = cfg.accepts[0].price if cfg.accepts else "$0.002"
        endpoints.append({
            "method": method,
            "path": path.replace(":", "{").replace("coin_id}", "coin_id}").replace("chain}", "chain}").replace("address}", "address}").replace("pair_id}", "pair_id}") if ":" in path else path,
            "price": price,
            "description": cfg.description or "",
        })
    return JSONResponse({
        "name": "x402 Crypto Intelligence API",
        "version": "4.0.0",
        "description": "AI agent crypto data API — pay per request in USDC on Base. 35+ endpoints: prices, DEX, DeFi, wallets, whale alerts, AI micro-SaaS. No API keys needed.",
        "url": base,
        "docs": f"{base}/docs",
        "payment": {
            "protocol": "x402",
            "version": 2,
            "network": "eip155:8453",
            "asset": "USDC",
            "asset_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "scheme": "exact",
            "pay_to": PAY_TO,
            "builder_code": BUILDER_CODE_APP,
        },
        "free_tier": [
            {"path": "/api/v1/free/health", "description": "API health + cache stats"},
            {"path": "/api/v1/free/fear-greed", "description": "Fear & Greed Index (basic)"},
            {"path": "/api/v1/free/gas", "description": "ETH gas prices (basic)"},
        ],
        "endpoints": endpoints,
        "tags": ["crypto", "defi", "blockchain", "ai-agent", "x402", "usdc", "base", "api", "market-data"],
        "category": "crypto-data",
        "github": "https://github.com/faisalnugroho/x402-crypto-api",
    })


@app.get("/shadowfeed/verify")
async def shadowfeed_verify():
    return {
        "status": "ok",
        "hmac_enabled": bool(SHADOWFEED_SECRET),
        "provider": "hermes-crypto",
        "endpoints_count": len(routes),
    }


@app.get("/favicon.ico")
async def favicon():
    from starlette.responses import Response
    gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
    return Response(content=gif, media_type="image/gif")


# Free tier endpoints (no payment required)
@app.get("/api/v1/free/health")
async def free_health():
    """Free: API health check with stats."""
    return {
        "status": "ok",
        "version": "3.0.0",
        "endpoints": len(routes),
        "uptime": "operational",
        "cache_stats": cache.stats(),
    }


@app.get("/api/v1/free/fear-greed")
async def free_fear_greed():
    """Free: Current Fear & Greed Index (limited)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://api.alternative.me/fng/?limit=1&format=json")
            data = r.json().get("data", [{}])[0] if r.status_code == 200 else {}
            return {
                "value": int(data.get("value", 0)),
                "label": data.get("value_classification"),
                "note": "Upgrade to /api/v1/sentiment for full analysis ($0.005)"
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/v1/free/gas")
async def free_gas():
    """Free: Basic gas prices (ETH only)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://api.etherscan.io/api?module=gastracker&action=gasoracle")
            if r.status_code == 200:
                result = r.json().get("result", {})
                return {
                    "ethereum": {
                        "low": result.get("SafeGasPrice"),
                        "standard": result.get("ProposeGasPrice"),
                        "fast": result.get("FastGasPrice"),
                    },
                    "unit": "Gwei",
                    "note": "Upgrade to /api/v1/gas/multi for 6 chains ($0.003)"
                }
    except Exception:
        pass
    return {"error": "Gas data temporarily unavailable"}


@app.get("/api/v1/free/price/{coin_id}")
async def free_price(coin_id: str):
    """Free: Basic price for top 20 coins (limited). Upgrade for full data."""
    TOP_COINS = {"bitcoin", "ethereum", "solana", "bnb", "xrp", "cardano",
                 "dogecoin", "avalanche-2", "polkadot", "chainlink", "tron",
                 "polygon", "litecoin", "near", "uniswap", "internet-computer",
                 "aptos", "stellar", "arbitrum", "optimism"}
    cid = coin_id.lower().strip()
    if cid not in TOP_COINS:
        return {"error": f"Free tier limited to top 20 coins. '{cid}' requires payment.",
                "upgrade": f"GET /api/v1/price/{cid} — $0.003 via x402",
                "free_coins": sorted(TOP_COINS)}
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(f"{COINGECKO_BASE}/simple/price",
                            params={"ids": cid, "vs_currencies": "usd", "include_24hr_change": "true"})
            if r.status_code == 200:
                d = r.json().get(cid, {})
                return {
                    "id": cid,
                    "price_usd": d.get("usd"),
                    "change_24h_pct": round(d.get("usd_24h_change", 0), 2),
                    "note": "Free tier: basic price only. Upgrade for market cap, volume, ATH ($0.003)",
                }
    except Exception:
        pass
    return {"error": "Price data temporarily unavailable"}


@app.get("/api/v1/free/market")
async def free_market():
    """Free: Basic global market overview (limited)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(f"{COINGECKO_BASE}/global")
            if r.status_code == 200:
                d = r.json().get("data", {})
                return {
                    "total_market_cap_usd": d.get("total_market_cap", {}).get("usd"),
                    "total_volume_24h_usd": d.get("total_volume", {}).get("usd"),
                    "btc_dominance_pct": round(d.get("market_cap_percentage", {}).get("btc", 0), 1),
                    "note": "Free tier: basic overview. Upgrade for full breakdown ($0.003)",
                }
    except Exception:
        pass
    return {"error": "Market data temporarily unavailable"}


@app.get("/api/v1/free/catalog")
async def free_catalog():
    """Free: Full endpoint catalog for agent discovery."""
    endpoints = []
    for route_key, cfg in routes.items():
        method, path = route_key.split(" ", 1)
        price = cfg.accepts[0].price if cfg.accepts else "$0.002"
        endpoints.append({"method": method, "path": path, "price": price,
                          "description": cfg.description or ""})
    return {
        "name": "x402 Crypto Intelligence API",
        "payment": "x402 protocol — USDC on Base (eip155:8453)",
        "how_to_pay": "Send GET request → receive 402 with payment details → pay via x402 → retry with payment header",
        "free_endpoints": ["/api/v1/free/health", "/api/v1/free/fear-greed",
                           "/api/v1/free/gas", "/api/v1/free/price/{coin_id}",
                           "/api/v1/free/market", "/api/v1/free/catalog"],
        "paid_endpoints": endpoints,
        "docs": "/docs",
    }


# === PAID ENDPOINTS ===
@cached(TTL_PRICE, "price")
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


@cached(TTL_TRENDING, "trending")
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


@cached(TTL_MARKET, "market")
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


@cached(TTL_MARKET, "top_coins")
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


@cached(120, "search")
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


@cached(TTL_DEFI, "defi")
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


@cached(120, "fear_greed")
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


@cached(30, "gas")
@app.get("/api/v1/gas")
async def get_gas():
    eth_gas = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://api.etherscan.io/api?module=gastracker&action=gasoracle")
            if r.status_code == 200:
                result = r.json().get("result", {})
                if isinstance(result, dict):
                    eth_gas = {
                        "low": result.get("SafeGasPrice"),
                        "standard": result.get("ProposeGasPrice"),
                        "fast": result.get("FastGasPrice"),
                    }
    except Exception:
        eth_gas = {}
    if not eth_gas:
        eth_gas = {"low": 0.10, "standard": 0.15, "fast": 0.20}
    return {
        "ethereum": eth_gas,
        "note": "Gas prices in Gwei. Other chains (Base, Polygon, BSC) are L2/Low-cost.",
        "base_estimate_usd": 0.001,
        "polygon_estimate_usd": 0.0001,
    }


# === ADMIN DASHBOARD ===
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>x402 Crypto API — Dashboard</title>
<style>
  :root { --bg: #0a0a0f; --card: #12121a; --border: #1e1e2e; --accent: #00d4aa;
          --accent2: #7c5cfc; --text: #e0e0e8; --muted: #6b7280; --red: #ef4444;
          --green: #22c55e; --yellow: #eab308; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'SF Mono', 'JetBrains Mono', monospace; }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
  h1 { color: var(--accent); font-size: 24px; margin-bottom: 4px; }
  .subtitle { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .stat-label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
  .stat-value { font-size: 28px; font-weight: 700; margin-top: 4px; }
  .stat-value.accent { color: var(--accent); }
  .stat-value.purple { color: var(--accent2); }
  .stat-value.green { color: var(--green); }
  .stat-value.yellow { color: var(--yellow); }
  .section { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
  .section-title { font-size: 14px; font-weight: 600; margin-bottom: 16px; }
  .bar-chart { display: flex; align-items: flex-end; gap: 3px; height: 120px; }
  .bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px; }
  .bar { background: var(--accent); border-radius: 3px 3px 0 0; min-height: 2px; width: 100%; }
  .bar.paid { background: var(--accent2); }
  .bar-label { font-size: 9px; color: var(--muted); writing-mode: vertical-lr; transform: rotate(180deg); max-height: 60px; overflow: hidden; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; color: var(--muted); font-weight: 500; padding: 8px 12px; border-bottom: 1px solid var(--border); }
  td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
  tr:hover { background: rgba(0, 212, 170, 0.05); }
  .badge { padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }
  .badge-paid { background: rgba(0, 212, 170, 0.15); color: var(--accent); }
  .badge-free { background: rgba(107, 114, 128, 0.15); color: var(--muted); }
  .badge-err { background: rgba(239, 68, 68, 0.15); color: var(--red); }
  .period-btns { display: flex; gap: 8px; margin-bottom: 16px; }
  .period-btn { background: var(--border); border: none; color: var(--muted); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; font-family: inherit; }
  .period-btn.active { background: var(--accent); color: var(--bg); }
  .refresh { color: var(--muted); font-size: 11px; float: right; cursor: pointer; }
  .refresh:hover { color: var(--accent); }
  .empty { color: var(--muted); text-align: center; padding: 40px; font-size: 13px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 600px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } .two-col { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div><h1>x402 Crypto API</h1><div class="subtitle">Monitoring Dashboard v3.0 — USDC on Base</div></div>
    <span class="refresh" onclick="loadStats()">↻ refresh</span>
  </div>
  <div class="period-btns">
    <button class="period-btn active" onclick="setPeriod(24, this)">24H</button>
    <button class="period-btn" onclick="setPeriod(72, this)">3D</button>
    <button class="period-btn" onclick="setPeriod(168, this)">7D</button>
    <button class="period-btn" onclick="setPeriod(0, this)">ALL</button>
  </div>
  <div class="stats-grid" id="statsGrid">
    <div class="stat-card"><div class="stat-label">Total Requests</div><div class="stat-value accent" id="s-total">-</div></div>
    <div class="stat-card"><div class="stat-label">Paid Requests</div><div class="stat-value purple" id="s-paid">-</div></div>
    <div class="stat-card"><div class="stat-label">Conversion Rate</div><div class="stat-value yellow" id="s-conv">-</div></div>
    <div class="stat-card"><div class="stat-label">Revenue (USDC)</div><div class="stat-value green" id="s-rev">-</div></div>
    <div class="stat-card"><div class="stat-label">Unique IPs</div><div class="stat-value" id="s-ips">-</div></div>
    <div class="stat-card"><div class="stat-label">Endpoints</div><div class="stat-value accent" id="s-ep">-</div></div>
  </div>

  <!-- Revenue & Money Flow (on-chain) -->
  <div class="section">
    <div class="section-title" style="display:flex;justify-content:space-between;align-items:center;">
      <span>💰 Revenue & Money Flow (On-Chain · Base)</span>
      <span class="refresh" onclick="loadRevenue()">↻ refresh</span>
    </div>
    <div class="stats-grid" style="margin-bottom:16px;">
      <div class="stat-card"><div class="stat-label">Total Received (all-time)</div><div class="stat-value green" id="r-total">-</div></div>
      <div class="stat-card"><div class="stat-label">Seller Wallet Balance</div><div class="stat-value accent" id="r-seller">-</div></div>
      <div class="stat-card"><div class="stat-label">Payments Received</div><div class="stat-value purple" id="r-count">-</div></div>
      <div class="stat-card"><div class="stat-label">Unique Payers</div><div class="stat-value yellow" id="r-payers">-</div></div>
    </div>
    <div style="font-size:12px;color:var(--muted);margin-bottom:12px;">
      Seller wallet: <a id="r-seller-link" href="#" target="_blank" style="color:var(--accent);text-decoration:none;">-</a>
      &nbsp;·&nbsp; Network: Base (eip155:8453) · Asset: USDC
    </div>
    <div class="two-col">
      <div>
        <div class="section-title" style="font-size:12px;">Top Payers (where money comes from)</div>
        <table id="payersTable"><thead><tr><th>Payer Address</th><th>Payments</th><th>Total USDC</th></tr></thead><tbody></tbody></table>
      </div>
      <div>
        <div class="section-title" style="font-size:12px;">Recent Incoming Payments</div>
        <div style="overflow-x:auto;max-height:280px;overflow-y:auto;">
          <table id="transfersTable"><thead><tr><th>Time</th><th>From</th><th>Amount</th><th>Tx</th></tr></thead><tbody></tbody></table>
        </div>
      </div>
    </div>
  </div>

  <div class="two-col">
    <div class="section"><div class="section-title">Request Volume (Hourly)</div><div class="bar-chart" id="hourlyChart"><div class="empty">No data</div></div></div>
    <div class="section"><div class="section-title">Daily Volume</div><div class="bar-chart" id="dailyChart"><div class="empty">No data</div></div></div>
  </div>
  <div class="section"><div class="section-title">Endpoint Breakdown</div><table id="endpointsTable"><thead><tr><th>Endpoint</th><th>Hits</th><th>Paid</th><th>Revenue</th></tr></thead><tbody></tbody></table></div>
  <div class="section"><div class="section-title">Recent Requests (Last 50)</div><div style="overflow-x:auto;"><table id="recentTable"><thead><tr><th>Time</th><th>Endpoint</th><th>Status</th><th>Type</th><th>MS</th><th>IP</th></tr></thead><tbody></tbody></table></div></div>
</div>
<script>
let currentPeriod = 24;
async function loadStats() {
  try {
    const hrs = currentPeriod === 0 ? 9999 : currentPeriod;
    const r = await fetch('/admin/api/stats?hours=' + hrs);
    const d = await r.json();
    document.getElementById('s-total').textContent = d.total_requests.toLocaleString();
    document.getElementById('s-paid').textContent = d.paid_requests.toLocaleString();
    document.getElementById('s-conv').textContent = d.conversion_rate + '%';
    document.getElementById('s-rev').textContent = '$' + d.revenue_usdc.toFixed(4);
    document.getElementById('s-ips').textContent = d.unique_ips.toLocaleString();
    document.getElementById('s-ep').textContent = (d.endpoints ? d.endpoints.length : 0);
    const chart = document.getElementById('hourlyChart');
    if (d.hourly && d.hourly.length > 0) {
      const maxReq = Math.max(...d.hourly.map(h => h.requests), 1);
      chart.innerHTML = d.hourly.map(h => {
        const hPx = Math.max((h.requests / maxReq) * 100, 2);
        return '<div class="bar-col"><div class="bar" style="height:' + hPx + 'px" title="' + h.requests + ' req"></div><div class="bar-label">' + h.hour + '</div></div>';
      }).join('');
    }
    const dChart = document.getElementById('dailyChart');
    if (d.daily && d.daily.length > 0) {
      const maxD = Math.max(...d.daily.map(dy => dy.requests), 1);
      dChart.innerHTML = d.daily.map(dy => {
        const hPx = Math.max((dy.requests / maxD) * 100, 2);
        return '<div class="bar-col"><div class="bar" style="height:' + hPx + 'px" title="' + dy.requests + ' req"></div><div class="bar-label">' + dy.day + '</div></div>';
      }).join('');
    }
    const eTbody = document.querySelector('#endpointsTable tbody');
    if (d.endpoints && d.endpoints.length > 0) {
      eTbody.innerHTML = d.endpoints.map(e =>
        '<tr><td>' + e.endpoint + '</td><td>' + e.hits + '</td><td>' + (e.paid || 0) + '</td><td>$' + e.revenue.toFixed(4) + '</td></tr>'
      ).join('');
    }
    const rTbody = document.querySelector('#recentTable tbody');
    if (d.recent && d.recent.length > 0) {
      rTbody.innerHTML = d.recent.map(r => {
        const badge = r.status === 200 ? '<span class="badge badge-paid">PAID</span>' :
                      r.status === 402 ? '<span class="badge badge-free">402</span>' :
                      '<span class="badge badge-err">' + r.status + '</span>';
        return '<tr><td>' + r.time + '</td><td>' + r.endpoint + '</td><td>' + r.status + '</td><td>' + badge + '</td><td>' + r.ms + '</td><td>' + (r.ip||'-') + '</td></tr>';
      }).join('');
    }
  } catch(e) { console.error('Dashboard error:', e); }
}
function setPeriod(h, el) { currentPeriod = h; document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active')); el.classList.add('active'); loadStats(); }

function shortAddr(a) { return a ? a.slice(0,6) + '…' + a.slice(-4) : '-'; }
function fmtTime(ts) {
  if (!ts) return '-';
  try { return new Date(ts).toLocaleString('id-ID', {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}); }
  catch(e) { return ts; }
}

async function loadRevenue() {
  try {
    const r = await fetch('/admin/api/revenue');
    const d = await r.json();
    if (d.error) { console.error('revenue error', d.error); return; }

    document.getElementById('r-total').textContent = '$' + (d.total_received_usdc||0).toFixed(4);
    document.getElementById('r-seller').textContent = '$' + (d.balances.seller_usdc||0).toFixed(4);
    document.getElementById('r-count').textContent = (d.transfer_count||0).toLocaleString();
    document.getElementById('r-payers').textContent = (d.payers ? d.payers.length : 0);

    const link = document.getElementById('r-seller-link');
    link.textContent = shortAddr(d.seller_wallet);
    link.href = d.basescan_seller;

    const pTbody = document.querySelector('#payersTable tbody');
    if (d.payers && d.payers.length) {
      pTbody.innerHTML = d.payers.map(p =>
        '<tr><td><a href="https://basescan.org/address/'+p.address+'" target="_blank" style="color:var(--accent);text-decoration:none;">'+shortAddr(p.address)+'</a></td><td>'+p.count+'</td><td>$'+p.total_usdc.toFixed(4)+'</td></tr>'
      ).join('');
    }

    const tTbody = document.querySelector('#transfersTable tbody');
    if (d.transfers && d.transfers.length) {
      tTbody.innerHTML = d.transfers.map(t =>
        '<tr><td>'+fmtTime(t.timestamp)+'</td><td>'+shortAddr(t.from)+'</td><td style="color:var(--green);">+$'+t.amount_usdc.toFixed(4)+'</td><td><a href="https://basescan.org/tx/'+t.tx+'" target="_blank" style="color:var(--accent2);text-decoration:none;">'+t.tx.slice(0,10)+'…</a></td></tr>'
      ).join('');
    }
  } catch(e) { console.error('loadRevenue error:', e); }
}

loadStats(); loadRevenue(); setInterval(loadStats, 30000); setInterval(loadRevenue, 60000);
</script>
</body>
</html>"""

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    return DASHBOARD_HTML


@app.get("/admin/api/stats", response_class=JSONResponse)
async def admin_stats_v2(hours: int = Query(default=24, le=168)):
    return tracker.get_stats(hours=hours)


@app.get("/admin/api/revenue", response_class=JSONResponse)
async def admin_revenue_onchain():
    """Real on-chain revenue data from Blockscout."""
    from revenue_onchain import get_revenue_summary
    return get_revenue_summary()


# === LANDING PAGE HTML ===
LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>x402 Crypto Intelligence API — Pay Per Request in USDC</title>
<meta name="description" content="AI agent crypto data API + AI micro-SaaS. 35 endpoints. Pay per request in USDC on Base. No API keys needed.">
<style>
  :root { --bg: #0a0a0f; --card: #12121a; --border: #1e1e2e; --accent: #00d4aa; --accent2: #7c5cfc; --text: #e0e0e8; --muted: #6b7280; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; }
  .hero { text-align: center; padding: 80px 20px 60px; max-width: 800px; margin: 0 auto; }
  .hero h1 { font-size: 48px; font-weight: 800; background: linear-gradient(135deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 16px; }
  .hero p { color: var(--muted); font-size: 18px; max-width: 600px; margin: 0 auto 32px; }
  .badge-row { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-bottom: 40px; }
  .badge { background: var(--card); border: 1px solid var(--border); padding: 8px 16px; border-radius: 8px; font-size: 13px; }
  .badge span { color: var(--accent); font-weight: 600; }
  .cta { display: inline-block; background: var(--accent); color: var(--bg); padding: 14px 32px; border-radius: 8px; font-weight: 700; font-size: 16px; text-decoration: none; margin: 8px; }
  .cta.secondary { background: var(--card); color: var(--text); border: 1px solid var(--border); }
  .features { max-width: 1000px; margin: 0 auto; padding: 0 20px 60px; }
  .features h2 { text-align: center; font-size: 28px; margin-bottom: 40px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }
  .card h3 { color: var(--accent); font-size: 16px; margin-bottom: 8px; }
  .card p { color: var(--muted); font-size: 14px; }
  .card .price { color: var(--accent2); font-weight: 700; font-size: 18px; margin-top: 12px; }
  .endpoints-table { max-width: 1200px; margin: 0 auto; padding: 0 20px 60px; }
  .endpoints-table h2 { text-align: center; font-size: 28px; margin-bottom: 24px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { text-align: left; color: var(--muted); font-weight: 500; padding: 12px 16px; border-bottom: 1px solid var(--border); }
  td { padding: 12px 16px; border-bottom: 1px solid var(--border); }
  tr:hover { background: rgba(0, 212, 170, 0.05); }
  .free-badge { background: rgba(34, 197, 94, 0.15); color: #22c55e; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .paid-badge { background: rgba(124, 92, 252, 0.15); color: #7c5cfc; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .footer { text-align: center; padding: 40px 20px; color: var(--muted); font-size: 13px; border-top: 1px solid var(--border); }
  code { background: var(--card); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
</style>
</head>
<body>
<div class="hero">
  <h1>x402 Crypto + AI API</h1>
  <p>AI agent crypto data layer + vertical AI micro-SaaS. 35 endpoints covering prices, DEX, DeFi, wallets, whale alerts, legal review, tax estimation, invoice parsing, and sentiment analysis. Pay per request in USDC on Base.</p>
  <div class="badge-row">
    <div class="badge"><span>35</span> Endpoints</div>
    <div class="badge"><span>$0.002</span> Starting Price</div>
    <div class="badge"><span>USDC</span> on Base</div>
    <div class="badge"><span>No</span> API Key Needed</div>
  </div>
  <a href="/docs" class="cta">View API Docs</a>
  <a href="/admin" class="cta secondary">Dashboard</a>
</div>

<div class="features">
  <h2>Data Categories</h2>
  <div class="grid">
    <div class="card">
      <h3>Market Data</h3>
      <p>Real-time prices, market caps, volume, trending tokens, Fear & Greed Index. Powered by CoinGecko.</p>
      <div class="price">$0.002 — $0.005</div>
    </div>
    <div class="card">
      <h3>DEX Intelligence</h3>
      <p>Trading pairs, liquidity, volume across all DEXes. Search any token on Solana, ETH, Base, BSC.</p>
      <div class="price">$0.002 — $0.003</div>
    </div>
    <div class="card">
      <h3>DeFi Analytics</h3>
      <p>TVL rankings, protocol data, chain TVL. All DeFi protocols via DefiLlama.</p>
      <div class="price">$0.002 — $0.003</div>
    </div>
    <div class="card">
      <h3>Wallet Tracking</h3>
      <p>Native balances, ERC-20 transfers, transaction history, internal txns across 12+ chains.</p>
      <div class="price">$0.003 — $0.005</div>
    </div>
    <div class="card">
      <h3>Whale Alerts</h3>
      <p>Large transaction detection. Track whale movements on Ethereum and other chains.</p>
      <div class="price">$0.010</div>
    </div>
    <div class="card">
      <h3>Premium Analytics</h3>
      <p>Token screener, multi-wallet portfolio, top movers, batch prices. Built for AI agents.</p>
      <div class="price">$0.002 — $0.008</div>
    </div>
    <div class="card" style="border-color: var(--accent2);">
      <h3 style="color: var(--accent2);">⚡ AI Micro-SaaS (NEW v4.0)</h3>
      <p>Vertical AI services for AI agents: legal contract review, Indonesian tax estimator, invoice parser, multi-language sentiment. Powered by Xiaomi MiMo (mimo-v2-flash).</p>
      <div class="price">$0.005 — $0.020</div>
    </div>
  </div>
</div>

<div class="endpoints-table">
  <h2>All Endpoints</h2>
  <table>
    <thead><tr><th>Endpoint</th><th>Price</th><th>Type</th></tr></thead>
    <tbody>
      <tr><td><code>GET /api/v1/free/health</code></td><td>Free</td><td><span class="free-badge">FREE</span></td></tr>
      <tr><td><code>GET /api/v1/free/fear-greed</code></td><td>Free</td><td><span class="free-badge">FREE</span></td></tr>
      <tr><td><code>GET /api/v1/free/gas</code></td><td>Free</td><td><span class="free-badge">FREE</span></td></tr>
      <tr><td><code>GET /api/v1/price/:coin_id</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/trending</code></td><td>$0.005</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/market</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/top-coins</code></td><td>$0.005</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/search?q=</code></td><td>$0.002</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/prices?ids=</code></td><td>$0.002</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/movers</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/sentiment</code></td><td>$0.005</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/screener</code></td><td>$0.005</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/portfolio?wallets=</code></td><td>$0.008</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/whale/ethereum</code></td><td>$0.010</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/dex/token/:chain/:addr</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/dex/pair/:chain/:pair</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/dex/search?q=</code></td><td>$0.002</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/dex/trending</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/dex/boosted</code></td><td>$0.002</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/protocols</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/tvl/:protocol</code></td><td>$0.002</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/chains</code></td><td>$0.002</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/wallet/:chain/:addr</code></td><td>$0.005</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/gas/multi</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/wallet/:c/:a/transactions</code></td><td>$0.005</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/wallet/:c/:a/tokens</code></td><td>$0.005</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/wallet/:c/:a/internal</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/contract/:c/:a/abi</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/token/:c/:a/info</code></td><td>$0.003</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/gas/:chain</code></td><td>$0.002</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>GET /api/v1/block/:chain/latest</code></td><td>$0.002</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td colspan="3" style="padding: 16px; color: var(--accent2); font-weight: 700;">⚡ AI Micro-SaaS v4.0 (POST endpoints)</td></tr>
      <tr><td><code>POST /api/v1/ai/sentiment</code></td><td>$0.005</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>POST /api/v1/ai/invoice-ocr</code></td><td>$0.010</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>POST /api/v1/ai/tax-id</code></td><td>$0.015</td><td><span class="paid-badge">PAID</span></td></tr>
      <tr><td><code>POST /api/v1/ai/legal-review</code></td><td>$0.020</td><td><span class="paid-badge">PAID</span></td></tr>
    </tbody>
  </table>
</div>

<div style="max-width: 600px; margin: 0 auto 60px; text-align: center;">
  <h2 style="margin-bottom: 16px;">Quick Start</h2>
  <div style="background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; text-align: left; font-family: monospace; font-size: 13px;">
    <div style="color: var(--muted);"># Free request (no payment)</div>
    <div>curl https://api.example.com/api/v1/free/fear-greed</div>
    <br>
    <div style="color: var(--muted);"># Paid request (x402 protocol handles payment)</div>
    <div>curl https://api.example.com/api/v1/price/bitcoin</div>
    <br>
    <div style="color: var(--muted);"># With API key (higher rate limit: 300/min)</div>
    <div>curl -H "x-api-key: YOUR_KEY" https://api.example.com/api/v1/sentiment</div>
  </div>
</div>

<div class="footer">
  <p>x402 Crypto Intelligence API v3.0 — Powered by x402 Protocol on Base</p>
  <p style="margin-top: 8px;">Data: CoinGecko • DexScreener • DefiLlama • Etherscan</p>
</div>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    log.info(f"Starting x402 Crypto API v3.0 on port {PORT}, paying to {PAY_TO}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
