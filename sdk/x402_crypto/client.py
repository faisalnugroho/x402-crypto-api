"""Async client for x402 Crypto Intelligence API."""
import httpx
from typing import Optional

class X402Client:
    """Python SDK for x402 Crypto Intelligence API.
    
    Usage:
        async with X402Client() as client:
            price = await client.token_price("bitcoin")
            sentiment = await client.market_sentiment()
    """
    
    def __init__(self, base_url: str = "http://localhost:4020", api_key: Optional[str] = None, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        headers = {"accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    async def _get(self, path: str, params: dict = None) -> dict:
        r = await self._client.get(f"{self.base_url}{path}", params=params)
        if r.status_code == 402:
            return {"error": "Payment required (x402)", "headers": dict(r.headers)}
        r.raise_for_status()
        return r.json()
    
    # Free endpoints
    async def health(self) -> dict:
        return await self._get("/api/v1/free/health")
    
    async def fear_greed_free(self) -> dict:
        return await self._get("/api/v1/free/fear-greed")
    
    async def gas_free(self) -> dict:
        return await self._get("/api/v1/free/gas")
    
    # Market data
    async def token_price(self, coin_id: str) -> dict:
        return await self._get(f"/api/v1/price/{coin_id}")
    
    async def trending(self) -> dict:
        return await self._get("/api/v1/trending")
    
    async def market(self) -> dict:
        return await self._get("/api/v1/market")
    
    async def top_coins(self, limit: int = 20) -> dict:
        return await self._get("/api/v1/top-coins", {"limit": limit})
    
    async def search(self, query: str) -> dict:
        return await self._get("/api/v1/search", {"q": query})
    
    async def batch_prices(self, ids: str) -> dict:
        return await self._get("/api/v1/prices", {"ids": ids})
    
    async def movers(self, limit: int = 10) -> dict:
        return await self._get("/api/v1/movers", {"limit": limit})
    
    async def sentiment(self) -> dict:
        return await self._get("/api/v1/sentiment")
    
    async def screener(self, min_mcap: float = 1e6, max_mcap: float = 1e10, min_volume: float = 1e5, sort_by: str = "volume_desc", limit: int = 20) -> dict:
        return await self._get("/api/v1/screener", {"min_mcap": min_mcap, "max_mcap": max_mcap, "min_volume": min_volume, "sort_by": sort_by, "limit": limit})
    
    # DEX
    async def dex_pairs(self, chain: str, address: str) -> dict:
        return await self._get(f"/api/v1/dex/token/{chain}/{address}")
    
    async def dex_pair(self, chain: str, pair_id: str) -> dict:
        return await self._get(f"/api/v1/dex/pair/{chain}/{pair_id}")
    
    async def dex_search(self, query: str) -> dict:
        return await self._get("/api/v1/dex/search", {"q": query})
    
    async def dex_trending(self) -> dict:
        return await self._get("/api/v1/dex/trending")
    
    async def dex_boosted(self) -> dict:
        return await self._get("/api/v1/dex/boosted")
    
    # DeFi
    async def protocols(self) -> dict:
        return await self._get("/api/v1/protocols")
    
    async def tvl(self, protocol: str) -> dict:
        return await self._get(f"/api/v1/tvl/{protocol}")
    
    async def chains(self) -> dict:
        return await self._get("/api/v1/chains")
    
    async def defi(self) -> dict:
        return await self._get("/api/v1/defi")
    
    # Wallet
    async def wallet_balance(self, chain: str, address: str) -> dict:
        return await self._get(f"/api/v1/wallet/{chain}/{address}")
    
    async def wallet_transactions(self, chain: str, address: str, page: int = 1, offset: int = 20) -> dict:
        return await self._get(f"/api/v1/wallet/{chain}/{address}/transactions", {"page": page, "offset": offset})
    
    async def wallet_tokens(self, chain: str, address: str, page: int = 1, offset: int = 20) -> dict:
        return await self._get(f"/api/v1/wallet/{chain}/{address}/tokens", {"page": page, "offset": offset})
    
    async def wallet_internal(self, chain: str, address: str, page: int = 1, offset: int = 20) -> dict:
        return await self._get(f"/api/v1/wallet/{chain}/{address}/internal", {"page": page, "offset": offset})
    
    async def portfolio(self, wallets: str) -> dict:
        return await self._get("/api/v1/portfolio", {"wallets": wallets})
    
    # Contract
    async def contract_abi(self, chain: str, address: str) -> dict:
        return await self._get(f"/api/v1/contract/{chain}/{address}/abi")
    
    async def token_info(self, chain: str, address: str) -> dict:
        return await self._get(f"/api/v1/token/{chain}/{address}/info")
    
    # Gas
    async def gas_multi(self) -> dict:
        return await self._get("/api/v1/gas/multi")
    
    async def gas(self, chain: str) -> dict:
        return await self._get(f"/api/v1/gas/{chain}")
    
    async def latest_block(self, chain: str) -> dict:
        return await self._get(f"/api/v1/block/{chain}/latest")
    
    # Whale
    async def whale_alerts(self, min_usd: float = 100000) -> dict:
        return await self._get("/api/v1/whale/ethereum", {"min_usd": min_usd})
    
    # Fear & Greed (paid)
    async def fear_greed(self) -> dict:
        return await self._get("/api/v1/fear-greed")
