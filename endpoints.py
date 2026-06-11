"""
Additional endpoints — DexScreener, DefiLlama, Wallet, Multi-chain Gas.
All data sources are FREE, no API keys required.
Responses are cached for faster delivery to requesters.
"""
from fastapi import APIRouter, Query
import httpx
import asyncio
import time
from cache import cached, TTL_PRICE, TTL_TRENDING, TTL_MARKET, TTL_DEFI, TTL_CHAINS, TTL_GAS, TTL_WALLET, TTL_DEX, TTL_SEARCH

router = APIRouter(prefix="/api/v1", tags=["v2"])

_dex_client = httpx.AsyncClient(
    timeout=15.0,
    headers={"accept": "application/json"},
    base_url="https://api.dexscreener.com",
)
_llama_client = httpx.AsyncClient(
    timeout=15.0,
    headers={"accept": "application/json"},
    base_url="https://api.llama.fi",
)
_cg_client = httpx.AsyncClient(
    timeout=15.0,
    headers={"accept": "application/json"},
    base_url="https://api.coingecko.com/api/v3",
)

_last_cg = 0.0
_last_dex = 0.0
_last_llama = 0.0


async def _rate_cg():
    global _last_cg
    wait = 6.5 - (time.time() - _last_cg)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_cg = time.time()


async def _rate_dex():
    global _last_dex
    wait = 0.5 - (time.time() - _last_dex)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_dex = time.time()


async def _rate_llama():
    global _last_llama
    wait = 1.0 - (time.time() - _last_llama)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_llama = time.time()


# ============================================================
# DEXSCREENER ENDPOINTS (free, no key, 60-300 req/min)
# ============================================================

CHAIN_MAP = {
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "base": "base",
    "bsc": "bsc", "bnb": "bsc",
    "polygon": "polygon", "matic": "polygon",
    "arbitrum": "arbitrum", "arb": "arbitrum",
    "avalanche": "avalanche", "avax": "avalanche",
    "optimism": "optimism", "op": "optimism",
    "fantom": "fantom", "ftm": "fantom",
    "gnosis": "gnosis",
    "moonbeam": "moonbeam",
    "cronos": "cronos",
    "pulsechain": "pulsechain",
    "sonic": "sonic",
}


@cached(TTL_DEX, "dex_token")
@router.get("/dex/token/{chain}/{address}")
async def dex_token_pairs(chain: str, address: str):
    """Get all DEX trading pairs for a token across all DEXes."""
    chain_id = CHAIN_MAP.get(chain.lower(), chain.lower())
    await _rate_dex()
    r = await _dex_client.get(f"/token-pairs/v1/{chain_id}/{address}")
    if r.status_code != 200:
        return {"error": f"DexScreener returned {r.status_code}", "chain": chain_id, "address": address}
    pairs = r.json()
    if not pairs:
        return {"error": "No pairs found", "chain": chain_id, "address": address, "hint": "Check chain name (eth/sol/base/bsc/polygon/arbitrum) and token address"}

    results = []
    for p in pairs[:20]:
        txns = p.get("txns", {})
        h1 = txns.get("h1", {})
        h6 = txns.get("h6", {})
        h24 = txns.get("h24", {})
        results.append({
            "chain": p.get("chainId"),
            "dex": p.get("dexId"),
            "pair_address": p.get("pairAddress"),
            "base_token": p.get("baseToken", {}).get("symbol"),
            "quote_token": p.get("quoteToken", {}).get("symbol"),
            "price_usd": p.get("priceUsd"),
            "price_native": p.get("priceNative"),
            "liquidity_usd": p.get("liquidity", {}).get("usd"),
            "volume_24h": p.get("volume", {}).get("h24"),
            "volume_6h": p.get("volume", {}).get("h6"),
            "volume_1h": p.get("volume", {}).get("h1"),
            "price_change_24h": p.get("priceChange", {}).get("h24"),
            "price_change_1h": p.get("priceChange", {}).get("h1"),
            "buys_24h": h24.get("buys"),
            "sells_24h": h24.get("sells"),
            "fdv": p.get("fdv"),
            "pair_created": p.get("pairCreatedAt"),
            "url": p.get("url"),
        })

    return {
        "chain": chain_id,
        "address": address,
        "pairs": results,
        "count": len(results),
        "source": "dexscreener",
    }


@cached(TTL_DEX, "dex_pair")
@router.get("/dex/pair/{chain}/{pair_id}")
async def dex_pair(chain: str, pair_id: str):
    """Get detailed info for a specific DEX pair."""
    chain_id = CHAIN_MAP.get(chain.lower(), chain.lower())
    await _rate_dex()
    r = await _dex_client.get(f"/latest/dex/pairs/{chain_id}/{pair_id}")
    if r.status_code != 200:
        return {"error": f"DexScreener returned {r.status_code}"}
    data = r.json()
    pairs = data.get("pairs") or data.get("pair")
    if not pairs:
        return {"error": "Pair not found", "chain": chain_id, "pair_id": pair_id}
    p = pairs[0] if isinstance(pairs, list) else pairs
    txns = p.get("txns", {})
    h1 = txns.get("h1", {})
    h6 = txns.get("h6", {})
    h24 = txns.get("h24", {})
    return {
        "chain": p.get("chainId"),
        "dex": p.get("dexId"),
        "pair_address": p.get("pairAddress"),
        "base_token": p.get("baseToken"),
        "quote_token": p.get("quoteToken"),
        "price_usd": p.get("priceUsd"),
        "price_native": p.get("priceNative"),
        "liquidity_usd": p.get("liquidity", {}).get("usd"),
        "volume": p.get("volume"),
        "price_change": p.get("priceChange"),
        "txns_1h": h1,
        "txns_6h": h6,
        "txns_24h": h24,
        "fdv": p.get("fdv"),
        "market_cap": p.get("marketCap"),
        "pair_created": p.get("pairCreatedAt"),
        "url": p.get("url"),
        "info": p.get("info"),
        "source": "dexscreener",
    }


@cached(TTL_SEARCH, "dex_search")
@router.get("/dex/search")
async def dex_search(q: str = Query(..., min_length=1)):
    """Search for tokens on DEX by name, symbol, or address."""
    await _rate_dex()
    r = await _dex_client.get(f"/search?q={q}")
    if r.status_code != 200:
        return {"error": f"DexScreener returned {r.status_code}"}
    data = r.json()
    pairs = data.get("pairs") or []
    results = []
    for p in pairs[:15]:
        results.append({
            "chain": p.get("chainId"),
            "dex": p.get("dexId"),
            "pair_address": p.get("pairAddress"),
            "base_token": p.get("baseToken", {}).get("symbol"),
            "base_name": p.get("baseToken", {}).get("name"),
            "base_address": p.get("baseToken", {}).get("address"),
            "quote_token": p.get("quoteToken", {}).get("symbol"),
            "price_usd": p.get("priceUsd"),
            "liquidity_usd": p.get("liquidity", {}).get("usd"),
            "volume_24h": p.get("volume", {}).get("h24"),
            "url": p.get("url"),
        })
    return {"query": q, "pairs": results, "count": len(results), "source": "dexscreener"}


@cached(TTL_TRENDING, "dex_trending")
@router.get("/dex/trending")
async def dex_trending():
    """Get trending tokens on DEX (recently updated profiles)."""
    await _rate_dex()
    r = await _dex_client.get("/token-profiles/recent-updates/v1")
    if r.status_code != 200:
        return {"error": f"DexScreener returned {r.status_code}"}
    profiles = r.json()
    results = []
    for p in (profiles or [])[:20]:
        results.append({
            "chain": p.get("chainId"),
            "token_address": p.get("tokenAddress"),
            "description": (p.get("description") or "")[:100],
            "links": p.get("links", [])[:3],
            "source": "dexscreener",
        })
    return {"trending": results, "count": len(results), "source": "dexscreener"}


@cached(TTL_TRENDING, "dex_boosted")
@router.get("/dex/boosted")
async def dex_boosted():
    """Get top boosted tokens on DEX (most active promotions)."""
    await _rate_dex()
    r = await _dex_client.get("/token-boosts/top/v1")
    if r.status_code != 200:
        return {"error": f"DexScreener returned {r.status_code}"}
    boosts = r.json()
    results = []
    for b in (boosts or [])[:20]:
        results.append({
            "chain": b.get("chainId"),
            "token_address": b.get("tokenAddress"),
            "amount": b.get("amount"),
            "source": "dexscreener",
        })
    return {"boosted": results, "count": len(results), "source": "dexscreener"}


# ============================================================
# DEFILLAMA ENDPOINTS (free, no key)
# ============================================================

@cached(TTL_DEFI, "protocols")
@router.get("/protocols")
async def all_protocols():
    """Get all DeFi protocols with TVL, chains, and category."""
    await _rate_llama()
    r = await _llama_client.get("/protocols")
    if r.status_code != 200:
        return {"error": f"DefiLlama returned {r.status_code}"}
    data = r.json()
    protocols = []
    for p in (data or [])[:50]:
        protocols.append({
            "name": p.get("name"),
            "slug": p.get("slug"),
            "category": p.get("category"),
            "tvl": p.get("tvl"),
            "change_1h": p.get("change_1h"),
            "change_1d": p.get("change_1d"),
            "change_7d": p.get("change_7d"),
            "chains": p.get("chains", []),
            "chain": p.get("chain"),
            "url": p.get("url"),
            "description": (p.get("description") or "")[:120],
        })
    return {"protocols": protocols, "count": len(protocols), "source": "defillama"}


@cached(TTL_DEFI, "tvl")
@router.get("/tvl/{protocol}")
async def protocol_tvl(protocol: str):
    """Get TVL history for a specific protocol."""
    await _rate_llama()
    r = await _llama_client.get(f"/tvl/{protocol}")
    if r.status_code != 200:
        return {"error": f"DefiLlama returned {r.status_code}", "hint": "Use protocol slug (e.g. 'aave', 'uniswap', 'lido')"}
    tvl = r.json()
    # Also get protocol details
    await _rate_llama()
    r2 = await _llama_client.get("/protocols")
    detail = {}
    if r2.status_code == 200:
        for p in r2.json():
            if p.get("slug", "").lower() == protocol.lower():
                detail = {
                    "name": p.get("name"),
                    "category": p.get("category"),
                    "chains": p.get("chains"),
                    "change_1d": p.get("change_1d"),
                    "change_7d": p.get("change_7d"),
                    "url": p.get("url"),
                }
                break
    return {"protocol": protocol, "current_tvl": tvl, "details": detail, "source": "defillama"}


@cached(TTL_CHAINS, "chains")
@router.get("/chains")
async def all_chains():
    """Get all supported blockchain chains with TVL data."""
    await _rate_llama()
    r = await _llama_client.get("/chains")
    if r.status_code != 200:
        return {"error": f"DefiLlama returned {r.status_code}"}
    chains = r.json()
    results = []
    for c in (chains or []):
        results.append({
            "name": c.get("name"),
            "chain_id": c.get("chainId"),
            "tvl": c.get("tvl"),
            "gecko_id": c.get("gecko_id"),
            "symbol": c.get("symbol"),
        })
    # Sort by TVL descending
    results.sort(key=lambda x: x.get("tvl") or 0, reverse=True)
    return {"chains": results[:50], "count": len(results), "source": "defillama"}


# ============================================================
# WALLET PORTFOLIO (via CoinGecko + public RPCs)
# ============================================================

# Public RPC endpoints (free, rate-limited)
RPC_ENDPOINTS = {
    "ethereum": "https://ethereum-rpc.publicnode.com",
    "base": "https://mainnet.base.org",
    "bsc": "https://bsc-rpc.publicnode.com",
    "polygon": "https://polygon-bor-rpc.publicnode.com",
    "arbitrum": "https://arbitrum-one-rpc.publicnode.com",
    "optimism": "https://optimism-rpc.publicnode.com",
}


@cached(TTL_WALLET, "wallet")
@router.get("/wallet/{chain}/{address}")
async def wallet_portfolio(chain: str, address: str):
    """Get native balance for an EVM wallet address."""
    chain_lower = chain.lower()
    rpc = RPC_ENDPOINTS.get(chain_lower)
    if not rpc:
        return {
            "error": f"Chain '{chain}' not supported",
            "supported": list(RPC_ENDPOINTS.keys()),
        }

    async with httpx.AsyncClient(timeout=10.0) as c:
        # Get native balance
        r = await c.post(rpc, json={
            "jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [address, "latest"], "id": 1,
        })
        if r.status_code != 200:
            return {"error": f"RPC returned {r.status_code}"}
        balance_hex = r.json().get("result", "0x0")
        balance_wei = int(balance_hex, 16)
        balance_native = balance_wei / 10**18

        # Get block number
        r2 = await c.post(rpc, json={
            "jsonrpc": "2.0", "method": "eth_blockNumber",
            "params": [], "id": 2,
        })
        block = int(r2.json().get("result", "0x0"), 16) if r2.status_code == 200 else 0

    # Get native token price from CoinGecko
    native_prices = {
        "ethereum": "ethereum", "base": "ethereum",
        "bsc": "binancecoin", "polygon": "matic-network",
        "arbitrum": "ethereum", "optimism": "ethereum",
    }
    cg_id = native_prices.get(chain_lower, "ethereum")
    try:
        await _rate_cg()
        r3 = await _cg_client.get("/simple/price", params={
            "ids": cg_id, "vs_currencies": "usd",
        })
        price_data = r3.json()
        native_price_usd = price_data.get(cg_id, {}).get("usd", 0)
    except Exception:
        native_price_usd = 0

    native_symbol = {"ethereum": "ETH", "base": "ETH", "bsc": "BNB",
                     "polygon": "MATIC", "arbitrum": "ETH", "optimism": "ETH"}.get(chain_lower, "ETH")

    return {
        "chain": chain_lower,
        "address": address,
        "native_balance": round(balance_native, 6),
        "native_symbol": native_symbol,
        "balance_usd": round(balance_native * native_price_usd, 2),
        "native_price_usd": native_price_usd,
        "block_number": block,
        "source": "on-chain",
    }


# ============================================================
# MULTI-CHAIN GAS (free endpoints)
# ============================================================

GAS_SOURCES = {
    "ethereum": None,  # Use public RPC
    "polygon": None,
    "bsc": None,
    "arbitrum": None,  # Will use public RPC
    "optimism": None,
    "base": None,
}

CHAIN_IDS = {
    "ethereum": "ethereum", "base": "base", "bsc": "bsc",
    "polygon": "polygon", "arbitrum": "arbitrum", "optimism": "optimism",
}


async def _get_gas_from_rpc(chain: str) -> dict:
    """Get gas price from public RPC."""
    rpc = RPC_ENDPOINTS.get(chain)
    if not rpc:
        return {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.post(rpc, json={
                "jsonrpc": "2.0", "method": "eth_gasPrice",
                "params": [], "id": 1,
            })
            if r.status_code == 200:
                gas_hex = r.json().get("result", "0x0")
                gas_wei = int(gas_hex, 16)
                gas_gwei = gas_wei / 10**9
                return {"low": round(gas_gwei * 0.8, 2),
                        "standard": round(gas_gwei, 2),
                        "fast": round(gas_gwei * 1.3, 2)}
    except Exception:
        pass
    return {}


@cached(TTL_GAS, "gas_multi")
@router.get("/gas/multi")
async def multi_chain_gas():
    """Get gas prices across multiple chains via public RPCs."""
    results = {}
    for chain in ["ethereum", "base", "bsc", "polygon", "arbitrum", "optimism"]:
        gas = await _get_gas_from_rpc(chain)
        if gas:
            gas["unit"] = "Gwei"
            gas["source"] = "public-rpc"
            results[chain] = gas

    return {"chains": results, "count": len(results), "source": "multi"}
