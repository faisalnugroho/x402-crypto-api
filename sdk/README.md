# x402 Crypto Python SDK

Async Python SDK for the x402 Crypto Intelligence API.

## Install

```bash
pip install x402-crypto
```

Or from source:
```bash
cd x402-crypto-api/sdk && pip install .
```

## Quick Start

```python
import asyncio
from x402_crypto import X402Client

async def main():
    async with X402Client("http://your-server:4020") as client:
        # Free endpoints
        health = await client.health()
        print(health)
        
        # Market data
        btc = await client.token_price("bitcoin")
        print(f"BTC: ${btc['price']:,.2f}")
        
        # Sentiment
        sentiment = await client.sentiment()
        print(f"Fear & Greed: {sentiment['fear_greed']['value']} ({sentiment['fear_greed']['label']})")
        
        # DEX search
        pairs = await client.dex_search("pepe")
        print(f"Found {pairs['count']} pairs")
        
        # Batch prices
        prices = await client.batch_prices("bitcoin,ethereum,solana")
        for coin, data in prices["prices"].items():
            print(f"{coin}: ${data['price_usd']:,.2f}")

asyncio.run(main())
```

## With API Key (higher rate limits)

```python
async with X402Client("http://your-server:4020", api_key="your-key") as client:
    # 300 req/min instead of 30
    data = await client.market()
```

## All Methods

| Method | Description |
|--------|-------------|
| `health()` | API health check |
| `token_price(coin_id)` | Token price & market data |
| `trending()` | Trending tokens |
| `market()` | Global market overview |
| `top_coins(limit)` | Top coins by mcap |
| `search(query)` | Search coins |
| `batch_prices(ids)` | Multiple prices at once |
| `movers(limit)` | Top gainers & losers |
| `sentiment()` | Market sentiment analysis |
| `screener(...)` | Token screener |
| `dex_pairs(chain, addr)` | DEX trading pairs |
| `dex_pair(chain, pair_id)` | DEX pair details |
| `dex_search(query)` | Search DEX tokens |
| `dex_trending()` | Trending DEX tokens |
| `dex_boosted()` | Top boosted tokens |
| `protocols()` | All DeFi protocols |
| `tvl(protocol)` | Protocol TVL |
| `chains()` | Chain TVL data |
| `defi()` | DeFi overview |
| `wallet_balance(chain, addr)` | Wallet balance |
| `wallet_transactions(chain, addr)` | Tx history |
| `wallet_tokens(chain, addr)` | Token transfers |
| `wallet_internal(chain, addr)` | Internal txns |
| `portfolio(wallets)` | Multi-wallet tracker |
| `contract_abi(chain, addr)` | Contract ABI |
| `token_info(chain, addr)` | Token info |
| `gas_multi()` | Multi-chain gas |
| `gas(chain)` | Chain gas prices |
| `latest_block(chain)` | Latest block |
| `whale_alerts(min_usd)` | Whale alerts |
| `fear_greed()` | Fear & Greed Index |
