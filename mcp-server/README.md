# x402 Crypto Intelligence MCP Server

MCP (Model Context Protocol) server that exposes 31 crypto data endpoints as tools for AI agents.

## Installation

```bash
pip install mcp httpx
```

## Usage

### With Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "x402-crypto": {
      "command": "python",
      "args": ["/path/to/x402-crypto-api/mcp-server/server.py"]
    }
  }
}
```

### With Hermes Agent
Add to Hermes config:
```yaml
mcp:
  servers:
    x402-crypto:
      command: python
      args: [~/x402-crypto-api/mcp-server/server.py]
```

### Standalone
```bash
python server.py
```

## Available Tools (31)

### Free (no payment)
- `crypto_health` — API health check
- `fear_greed_index` — Fear & Greed Index
- `gas_prices` — ETH gas prices

### Market Data
- `token_price(coin_id)` — Real-time price & market data
- `trending_tokens()` — Currently trending tokens
- `global_market()` — Global market overview
- `top_coins(limit)` — Top coins by market cap
- `search_coins(query)` — Search by name/symbol
- `batch_prices(ids)` — Multiple prices at once
- `top_movers(limit)` — Top gainers & losers
- `market_sentiment()` — Full sentiment analysis
- `token_screener(...)` — Screen by mcap/volume

### DEX Intelligence
- `dex_token_pairs(chain, address)` — All DEX pairs
- `dex_pair_info(chain, pair_id)` — Pair details
- `dex_search(query)` — Search DEX tokens
- `dex_trending()` — Trending DEX tokens
- `dex_boosted()` — Top boosted tokens

### DeFi Analytics
- `defi_protocols()` — All DeFi protocols
- `protocol_tvl(protocol)` — Protocol TVL
- `blockchain_chains()` — Chain TVL data
- `defi_overview()` — DeFi market overview

### Wallet Tracking
- `wallet_balance(chain, address)` — Native balance
- `wallet_transactions(chain, address)` — Tx history
- `wallet_token_transfers(chain, address)` — ERC-20 transfers
- `wallet_internal_txs(chain, address)` — Internal txns
- `multi_wallet_portfolio(wallets)` — Multi-wallet tracker

### Contract & Token
- `contract_abi(chain, address)` — Contract ABI
- `token_info(chain, address)` — Token info

### Gas & Chain
- `multi_chain_gas()` — Gas across 6 chains
- `etherscan_gas(chain)` — Accurate gas prices
- `latest_block(chain)` — Latest block number

### Whale Alerts
- `whale_alerts(min_usd)` — Large ETH transfers

## Data Sources
- CoinGecko (prices, market data)
- DexScreener (DEX pairs, trending)
- DefiLlama (DeFi TVL, protocols)
- Etherscan (wallet history, contracts)
- Public RPCs (on-chain data)
