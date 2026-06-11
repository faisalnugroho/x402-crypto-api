"""
New high-value endpoints — Whale alerts, Sentiment, Portfolio, Token Screener.
All use free data sources, no API keys required.
"""
from fastapi import APIRouter, Query
import httpx
import asyncio
import time
from cache import cached

router = APIRouter(prefix="/api/v1", tags=["premium"])

# ============================================================
# WHALE ALERTS (via public blockchain explorers)
# ============================================================

@cached(300, "whale_eth")
@router.get("/whale/ethereum")
async def whale_alerts_eth(min_usd: float = Query(default=100000, ge=1000)):
    """Get recent large ETH transfers (whale movements) via Etherscan."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            # Get latest blocks and large transfers
            r = await c.get("https://api.etherscan.io/api", params={
                "module": "proxy", "action": "eth_getBlockByNumber",
                "tag": "latest", "boolean": "true"
            })
            if r.status_code != 200:
                return {"error": "Etherscan unavailable"}
            
            block = r.json().get("result", {})
            txs = block.get("transactions", [])
            
            # Get ETH price
            r2 = await c.get("https://api.coingecko.com/api/v3/simple/price", 
                           params={"ids": "ethereum", "vs_currencies": "usd"})
            eth_price = r2.json().get("ethereum", {}).get("usd", 0) if r2.status_code == 200 else 0
            
            whales = []
            for tx in txs[:50]:
                value_wei = int(tx.get("value", "0x0"), 16)
                value_eth = value_wei / 10**18
                value_usd = value_eth * eth_price
                
                if value_usd >= min_usd:
                    whales.append({
                        "hash": tx.get("hash"),
                        "from": tx.get("from"),
                        "to": tx.get("to"),
                        "value_eth": round(value_eth, 4),
                        "value_usd": round(value_usd, 2),
                        "type": "transfer" if not tx.get("to") else "contract_call" if len(tx.get("input", "")) > 10 else "transfer"
                    })
            
            return {
                "chain": "ethereum",
                "min_usd": min_usd,
                "whales": whales,
                "count": len(whales),
                "eth_price_usd": eth_price,
                "block_number": int(block.get("number", "0x0"), 16),
                "source": "etherscan"
            }
    except Exception as e:
        return {"error": str(e)}


@cached(300, "whale_sol")
@router.get("/whale/solana")
async def whale_alerts_sol(min_usd: float = Query(default=50000, ge=1000)):
    """Get recent large SOL transfers via Solana public API."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            # Get SOL price
            r = await c.get("https://api.coingecko.com/api/v3/simple/price",
                          params={"ids": "solana", "vs_currencies": "usd"})
            sol_price = r.json().get("solana", {}).get("usd", 0) if r.status_code == 200 else 0
            
            return {
                "chain": "solana",
                "min_usd": min_usd,
                "sol_price_usd": sol_price,
                "note": "Solana whale tracking requires dedicated RPC. Use /api/v1/dex/token/solana/{address} for specific tokens.",
                "source": "coingecko"
            }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# MARKET SENTIMENT (Fear & Greed + Social)
# ============================================================

@cached(300, "sentiment")
@router.get("/sentiment")
async def market_sentiment():
    """Get comprehensive market sentiment data."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            # Fear & Greed Index
            r1 = await c.get("https://api.alternative.me/fng/?limit=30&format=json")
            fng = r1.json().get("data", []) if r1.status_code == 200 else []
            
            # BTC dominance and market data
            r2 = await c.get("https://api.coingecko.com/api/v3/global")
            global_data = r2.json().get("data", {}) if r2.status_code == 200 else {}
            
            # Trending searches
            r3 = await c.get("https://api.coingecko.com/api/v3/search/trending")
            trending = r3.json().get("coins", [])[:5] if r3.status_code == 200 else []
            
            current_fng = fng[0] if fng else {}
            
            return {
                "fear_greed": {
                    "value": int(current_fng.get("value", 0)),
                    "label": current_fng.get("value_classification"),
                    "history_7d": [
                        {"date": e.get("timestamp"), "value": int(e.get("value", 0))}
                        for e in fng[:7]
                    ]
                },
                "market": {
                    "total_mcap_usd": global_data.get("total_market_cap", {}).get("usd"),
                    "total_volume_24h": global_data.get("total_volume", {}).get("usd"),
                    "btc_dominance": global_data.get("market_cap_percentage", {}).get("btc"),
                    "eth_dominance": global_data.get("market_cap_percentage", {}).get("eth"),
                    "mcap_change_24h": global_data.get("market_cap_change_percentage_24h_usd"),
                },
                "trending_coins": [
                    {"name": t.get("item", {}).get("name"), "symbol": t.get("item", {}).get("symbol")}
                    for t in trending
                ],
                "interpretation": _interpret_sentiment(int(current_fng.get("value", 50))),
                "source": "alternative.me + coingecko"
            }
    except Exception as e:
        return {"error": str(e)}


def _interpret_sentiment(value: int) -> str:
    if value <= 20:
        return "EXTREME FEAR — Potential buying opportunity. Market is oversold."
    elif value <= 40:
        return "FEAR — Market sentiment is bearish. May be good entry points."
    elif value <= 60:
        return "NEUTRAL — Market is balanced. No strong directional bias."
    elif value <= 80:
        return "GREED — Market is bullish. Consider taking profits."
    else:
        return "EXTREME GREED — Market may be overbought. High risk of correction."


# ============================================================
# TOKEN SCREENER (multi-source)
# ============================================================

@cached(120, "screener")
@router.get("/screener")
async def token_screener(
    min_mcap: float = Query(default=1000000, description="Min market cap USD"),
    max_mcap: float = Query(default=10000000000, description="Max market cap USD"),
    min_volume: float = Query(default=100000, description="Min 24h volume USD"),
    sort_by: str = Query(default="volume_desc", description="Sort: volume_desc, mcap_desc, change_desc"),
    limit: int = Query(default=20, le=50)
):
    """Screen tokens by market cap, volume, and price change criteria."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get("https://api.coingecko.com/api/v3/coins/markets", params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": "250",
                "page": "1",
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d"
            })
            if r.status_code != 200:
                return {"error": f"CoinGecko returned {r.status_code}"}
            
            coins = r.json()
            
            # Filter
            filtered = []
            for c in coins:
                mcap = c.get("market_cap", 0) or 0
                vol = c.get("total_volume", 0) or 0
                if min_mcap <= mcap <= max_mcap and vol >= min_volume:
                    filtered.append({
                        "id": c.get("id"),
                        "symbol": c.get("symbol"),
                        "name": c.get("name"),
                        "price": c.get("current_price"),
                        "market_cap": mcap,
                        "volume_24h": vol,
                        "change_1h": c.get("price_change_percentage_1h_in_currency"),
                        "change_24h": c.get("price_change_percentage_24h_in_currency"),
                        "change_7d": c.get("price_change_percentage_7d_in_currency"),
                        "rank": c.get("market_cap_rank"),
                    })
            
            # Sort
            if sort_by == "volume_desc":
                filtered.sort(key=lambda x: x["volume_24h"], reverse=True)
            elif sort_by == "mcap_desc":
                filtered.sort(key=lambda x: x["market_cap"], reverse=True)
            elif sort_by == "change_desc":
                filtered.sort(key=lambda x: x.get("change_24h") or 0, reverse=True)
            
            return {
                "filters": {"min_mcap": min_mcap, "max_mcap": max_mcap, "min_volume": min_volume},
                "results": filtered[:limit],
                "total_matching": len(filtered),
                "sort": sort_by,
                "source": "coingecko"
            }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# PORTFOLIO TRACKER (multi-wallet)
# ============================================================

@cached(30, "portfolio")
@router.get("/portfolio")
async def portfolio_tracker(
    wallets: str = Query(..., description="Comma-separated chain:address pairs (e.g. ethereum:0xabc,base:0xdef)")
):
    """Track portfolio across multiple wallets and chains."""
    try:
        pairs = [w.strip() for w in wallets.split(",") if w.strip()]
        if len(pairs) > 10:
            return {"error": "Max 10 wallets per request"}
        
        from endpoints import RPC_ENDPOINTS, CHAIN_MAP
        
        results = []
        total_usd = 0
        
        async with httpx.AsyncClient(timeout=15.0) as c:
            # Get prices for all native tokens
            r = await c.get("https://api.coingecko.com/api/v3/simple/price", params={
                "ids": "ethereum,binancecoin,matic-network",
                "vs_currencies": "usd"
            })
            prices = r.json() if r.status_code == 200 else {}
            
            native_prices = {
                "ethereum": prices.get("ethereum", {}).get("usd", 0),
                "base": prices.get("ethereum", {}).get("usd", 0),
                "bsc": prices.get("binancecoin", {}).get("usd", 0),
                "polygon": prices.get("matic-network", {}).get("usd", 0),
                "arbitrum": prices.get("ethereum", {}).get("usd", 0),
                "optimism": prices.get("ethereum", {}).get("usd", 0),
            }
            
            for pair in pairs:
                parts = pair.split(":")
                if len(parts) != 2:
                    results.append({"input": pair, "error": "Format: chain:address"})
                    continue
                
                chain, address = parts[0].lower(), parts[1]
                rpc = RPC_ENDPOINTS.get(chain)
                if not rpc:
                    results.append({"chain": chain, "address": address, "error": f"Unsupported chain"})
                    continue
                
                try:
                    r = await c.post(rpc, json={
                        "jsonrpc": "2.0", "method": "eth_getBalance",
                        "params": [address, "latest"], "id": 1
                    })
                    balance_hex = r.json().get("result", "0x0")
                    balance = int(balance_hex, 16) / 10**18
                    price = native_prices.get(chain, 0)
                    usd_value = balance * price
                    total_usd += usd_value
                    
                    results.append({
                        "chain": chain,
                        "address": address,
                        "balance": round(balance, 6),
                        "usd_value": round(usd_value, 2),
                        "token": {"ethereum": "ETH", "base": "ETH", "bsc": "BNB", 
                                 "polygon": "MATIC", "arbitrum": "ETH", "optimism": "ETH"}.get(chain, "ETH")
                    })
                except Exception as e:
                    results.append({"chain": chain, "address": address, "error": str(e)})
        
        return {
            "wallets": results,
            "total_usd": round(total_usd, 2),
            "wallet_count": len(results),
            "source": "on-chain + coingecko"
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# TOP GAINERS / LOSERS (24h)
# ============================================================

@cached(120, "movers")
@router.get("/movers")
async def top_movers(limit: int = Query(default=10, le=25)):
    """Get top gainers and losers in the last 24 hours."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get("https://api.coingecko.com/api/v3/coins/markets", params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": "250",
                "page": "1",
                "sparkline": "false",
                "price_change_percentage": "24h"
            })
            if r.status_code != 200:
                return {"error": f"CoinGecko returned {r.status_code}"}
            
            coins = r.json()
            valid = [c for c in coins if c.get("price_change_percentage_24h_in_currency") is not None]
            
            gainers = sorted(valid, key=lambda x: x["price_change_percentage_24h_in_currency"], reverse=True)[:limit]
            losers = sorted(valid, key=lambda x: x["price_change_percentage_24h_in_currency"])[:limit]
            
            def format_coin(c):
                return {
                    "id": c.get("id"),
                    "symbol": c.get("symbol"),
                    "name": c.get("name"),
                    "price": c.get("current_price"),
                    "change_24h": round(c.get("price_change_percentage_24h_in_currency", 0), 2),
                    "volume_24h": c.get("total_volume"),
                    "market_cap": c.get("market_cap"),
                }
            
            return {
                "gainers": [format_coin(c) for c in gainers],
                "losers": [format_coin(c) for c in losers],
                "timestamp": int(time.time()),
                "source": "coingecko"
            }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# QUICK PRICE (multiple tokens at once)
# ============================================================

@cached(30, "prices_batch")
@router.get("/prices")
async def batch_prices(ids: str = Query(..., description="Comma-separated coin IDs (e.g. bitcoin,ethereum,solana)")):
    """Get prices for multiple tokens in a single call (efficient batch)."""
    try:
        coin_list = [c.strip() for c in ids.split(",") if c.strip()]
        if len(coin_list) > 50:
            return {"error": "Max 50 tokens per request"}
        
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get("https://api.coingecko.com/api/v3/simple/price", params={
                "ids": ",".join(coin_list),
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            })
            if r.status_code != 200:
                return {"error": f"CoinGecko returned {r.status_code}"}
            
            data = r.json()
            results = {}
            for coin_id in coin_list:
                if coin_id in data:
                    d = data[coin_id]
                    results[coin_id] = {
                        "price_usd": d.get("usd"),
                        "market_cap": d.get("usd_market_cap"),
                        "volume_24h": d.get("usd_24h_vol"),
                        "change_24h": d.get("usd_24h_change"),
                    }
                else:
                    results[coin_id] = {"error": "Not found"}
            
            return {"prices": results, "count": len(results), "source": "coingecko"}
    except Exception as e:
        return {"error": str(e)}
