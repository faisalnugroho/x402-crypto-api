#!/usr/bin/env python3
"""
x402 Crypto Intelligence MCP Server
Exposes 31 crypto data endpoints as MCP tools for AI agents.
"""
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("x402-crypto", description="Crypto intelligence data via x402 protocol. Prices, DEX, DeFi, wallets, whale alerts.")

BASE = "http://localhost:4020"
client = httpx.AsyncClient(timeout=30.0)

async def _get(path: str, params: dict = None) -> dict:
    """Make API call to x402 Crypto API."""
    r = await client.get(f"{BASE}{path}", params=params)
    if r.status_code == 402:
        return {"error": "Payment required (x402 protocol)", "price": r.headers.get("x-payment-required", "unknown")}
    r.raise_for_status()
    return r.json()

# === FREE TOOLS ===
@mcp.tool()
async def crypto_health() -> dict:
    """Check API health, version, and cache stats."""
    return await _get("/api/v1/free/health")

@mcp.tool()
async def fear_greed_index() -> dict:
    """Get current Crypto Fear & Greed Index (free)."""
    return await _get("/api/v1/free/fear-greed")

@mcp.tool()
async def gas_prices() -> dict:
    """Get basic Ethereum gas prices in Gwei (free)."""
    return await _get("/api/v1/free/gas")

# === MARKET DATA TOOLS ===
@mcp.tool()
async def token_price(coin_id: str) -> dict:
    """Get real-time price, market cap, volume, and 24h change for a token. Example: bitcoin, ethereum, solana."""
    return await _get(f"/api/v1/price/{coin_id}")

@mcp.tool()
async def trending_tokens() -> dict:
    """Get currently trending crypto tokens."""
    return await _get("/api/v1/trending")

@mcp.tool()
async def global_market() -> dict:
    """Get global crypto market overview: total market cap, volume, BTC/ETH dominance."""
    return await _get("/api/v1/market")

@mcp.tool()
async def top_coins(limit: int = 20) -> dict:
    """Get top N coins by market cap with price changes. Limit: 1-100."""
    return await _get("/api/v1/top-coins", {"limit": limit})

@mcp.tool()
async def search_coins(query: str) -> dict:
    """Search for cryptocurrencies by name or symbol."""
    return await _get("/api/v1/search", {"q": query})

@mcp.tool()
async def batch_prices(ids: str) -> dict:
    """Get prices for multiple tokens at once. Comma-separated IDs (e.g. bitcoin,ethereum,solana). Max 50."""
    return await _get("/api/v1/prices", {"ids": ids})

@mcp.tool()
async def top_movers(limit: int = 10) -> dict:
    """Get top gainers and losers in the last 24 hours."""
    return await _get("/api/v1/movers", {"limit": limit})

@mcp.tool()
async def market_sentiment() -> dict:
    """Get comprehensive market sentiment: Fear & Greed, market data, trending coins, interpretation."""
    return await _get("/api/v1/sentiment")

@mcp.tool()
async def token_screener(min_mcap: float = 1000000, max_mcap: float = 10000000000, min_volume: float = 100000, sort_by: str = "volume_desc", limit: int = 20) -> dict:
    """Screen tokens by market cap, volume, and price change. Sort: volume_desc, mcap_desc, change_desc."""
    return await _get("/api/v1/screener", {"min_mcap": min_mcap, "max_mcap": max_mcap, "min_volume": min_volume, "sort_by": sort_by, "limit": limit})

# === DEX TOOLS ===
@mcp.tool()
async def dex_token_pairs(chain: str, address: str) -> dict:
    """Get all DEX trading pairs for a token. Chains: ethereum, solana, base, bsc, polygon, arbitrum."""
    return await _get(f"/api/v1/dex/token/{chain}/{address}")

@mcp.tool()
async def dex_pair_info(chain: str, pair_id: str) -> dict:
    """Get detailed info for a specific DEX pair (liquidity, volume, txns)."""
    return await _get(f"/api/v1/dex/pair/{chain}/{pair_id}")

@mcp.tool()
async def dex_search(query: str) -> dict:
    """Search for tokens on DEX by name, symbol, or address."""
    return await _get("/api/v1/dex/search", {"q": query})

@mcp.tool()
async def dex_trending() -> dict:
    """Get trending tokens on DEX (recently updated profiles)."""
    return await _get("/api/v1/dex/trending")

@mcp.tool()
async def dex_boosted() -> dict:
    """Get top boosted tokens on DEX (most active promotions)."""
    return await _get("/api/v1/dex/boosted")

# === DEFI TOOLS ===
@mcp.tool()
async def defi_protocols() -> dict:
    """Get all DeFi protocols with TVL, chains, and category."""
    return await _get("/api/v1/protocols")

@mcp.tool()
async def protocol_tvl(protocol: str) -> dict:
    """Get TVL history for a specific DeFi protocol (e.g. aave, uniswap, lido)."""
    return await _get(f"/api/v1/tvl/{protocol}")

@mcp.tool()
async def blockchain_chains() -> dict:
    """Get all supported blockchain chains with TVL data."""
    return await _get("/api/v1/chains")

@mcp.tool()
async def defi_overview() -> dict:
    """Get DeFi market overview: total DeFi market cap, trading volume, top DeFi coins."""
    return await _get("/api/v1/defi")

# === WALLET TOOLS ===
@mcp.tool()
async def wallet_balance(chain: str, address: str) -> dict:
    """Get native balance and USD value for an EVM wallet. Chains: ethereum, base, bsc, polygon, arbitrum, optimism."""
    return await _get(f"/api/v1/wallet/{chain}/{address}")

@mcp.tool()
async def wallet_transactions(chain: str, address: str, page: int = 1, offset: int = 20) -> dict:
    """Get transaction history for a wallet. Shows ETH transfers and contract calls."""
    return await _get(f"/api/v1/wallet/{chain}/{address}/transactions", {"page": page, "offset": offset})

@mcp.tool()
async def wallet_token_transfers(chain: str, address: str, page: int = 1, offset: int = 20) -> dict:
    """Get ERC-20 token transfer history for a wallet."""
    return await _get(f"/api/v1/wallet/{chain}/{address}/tokens", {"page": page, "offset": offset})

@mcp.tool()
async def wallet_internal_txs(chain: str, address: str, page: int = 1, offset: int = 20) -> dict:
    """Get internal transactions (contract calls) for a wallet."""
    return await _get(f"/api/v1/wallet/{chain}/{address}/internal", {"page": page, "offset": offset})

@mcp.tool()
async def multi_wallet_portfolio(wallets: str) -> dict:
    """Track portfolio across multiple wallets. Format: chain:address,chain:address (e.g. ethereum:0xabc,base:0xdef). Max 10 wallets."""
    return await _get("/api/v1/portfolio", {"wallets": wallets})

# === CONTRACT & TOKEN TOOLS ===
@mcp.tool()
async def contract_abi(chain: str, address: str) -> dict:
    """Get smart contract ABI, source code, and function list."""
    return await _get(f"/api/v1/contract/{chain}/{address}/abi")

@mcp.tool()
async def token_info(chain: str, address: str) -> dict:
    """Get ERC-20 token info: name, symbol, total supply, holders."""
    return await _get(f"/api/v1/token/{chain}/{address}/info")

# === GAS & CHAIN TOOLS ===
@mcp.tool()
async def multi_chain_gas() -> dict:
    """Get gas prices across 6 chains: ETH, Base, BSC, Polygon, Arbitrum, Optimism."""
    return await _get("/api/v1/gas/multi")

@mcp.tool()
async def etherscan_gas(chain: str) -> dict:
    """Get accurate gas prices from Etherscan Gas Tracker for any supported chain."""
    return await _get(f"/api/v1/gas/{chain}")

@mcp.tool()
async def latest_block(chain: str) -> dict:
    """Get latest block number for any Etherscan-supported chain."""
    return await _get(f"/api/v1/block/{chain}/latest")

# === WHALE TOOLS ===
@mcp.tool()
async def whale_alerts(min_usd: float = 100000) -> dict:
    """Get recent large ETH transfers (whale movements). Default: $100k+ transfers."""
    return await _get("/api/v1/whale/ethereum", {"min_usd": min_usd})

if __name__ == "__main__":
    mcp.run()
