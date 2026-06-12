# x402 Crypto Intelligence API — Promotion Kit

## Tagline
"The AI agent crypto data layer. 30+ endpoints. Pay per request in USDC on Base. No API keys."

## URL
http://43.157.206.248:4020

## Key Selling Points
1. **No API keys** — pay per request via x402 protocol (HTTP 402 + USDC)
2. **30+ endpoints** — prices, DEX, DeFi, wallets, whale alerts, gas
3. **Starting at $0.002** — micropayments, no subscriptions
4. **AI agent native** — built for autonomous agents, MCP server included
5. **Multi-source** — CoinGecko, DexScreener, DefiLlama, Etherscan
6. **Free tier** — 3 endpoints free to try

## Endpoints Summary

### Free (no payment)
- GET /api/v1/free/health — API status
- GET /api/v1/free/fear-greed — Fear & Greed Index
- GET /api/v1/free/gas — ETH gas prices

### Market Data ($0.002-$0.005)
- /api/v1/price/:coin_id — Token price & 24h data
- /api/v1/trending — Trending tokens
- /api/v1/market — Global market overview
- /api/v1/top-coins — Top coins by mcap
- /api/v1/search?q= — Search coins
- /api/v1/defi — DeFi protocols by TVL
- /api/v1/fear-greed — Fear & Greed Index
- /api/v1/gas — Multi-chain gas

### DEX Intelligence ($0.002-$0.003)
- /api/v1/dex/token/:chain/:address — DEX trading pairs
- /api/v1/dex/pair/:chain/:pair_id — Pair details
- /api/v1/dex/search?q= — Search DEX tokens
- /api/v1/dex/trending — Trending DEX tokens
- /api/v1/dex/boosted — Top boosted tokens

### DeFi Analytics ($0.002-$0.003)
- /api/v1/protocols — All DeFi protocols
- /api/v1/tvl/:protocol — Protocol TVL
- /api/v1/chains — Supported chains

### Wallet Tracking ($0.003-$0.005)
- /api/v1/wallet/:chain/:address — Native balance
- /api/v1/wallet/:chain/:address/transactions — TX history
- /api/v1/wallet/:chain/:address/tokens — ERC-20 transfers
- /api/v1/wallet/:chain/:address/internal — Internal TXs

### Contract & Token ($0.003)
- /api/v1/contract/:chain/:address/abi — Contract ABI
- /api/v1/token/:chain/:address/info — Token info

### Chain Data ($0.002-$0.003)
- /api/v1/gas/:chain — Etherscan gas tracker
- /api/v1/gas/multi — Multi-chain gas
- /api/v1/block/:chain/latest — Latest block

## Quick Start
```bash
# Free endpoint (no payment)
curl http://43.157.206.248:4020/api/v1/free/fear-greed

# Paid endpoint (returns 402 with payment instructions)
curl http://43.157.206.248:4020/api/v1/price/bitcoin
```

## Target Audiences
1. AI agent developers (need crypto data for bots)
2. DeFi researchers (need protocol/TVL data)
3. Crypto traders (need DEX/whale data)
4. MCP/Claude users (MCP server available)
5. Web3 data analysts

## Promotion Channels
- Reddit: r/cryptocurrency, r/defi, r/web3, r/MachineLearning
- X/Twitter: #cryptoAPI, #web3, #AIagent, #x402
- GitHub: public repo with docs + examples
- Discord: Coinbase Dev, Base, AI agent communities
- Telegram: Web3 dev groups
- API directories: api.market, RapidAPI, APILayer
- x402 Bazaar: Coinbase CDP listing
