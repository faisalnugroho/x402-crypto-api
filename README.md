# x402 Crypto Intelligence API

AI agent crypto data API — pay per request in USDC on Base. No API keys needed.

## What is this?

An HTTP API that serves real-time cryptocurrency data from CoinGecko, DexScreener, DefiLlama, and Etherscan, protected by the [x402 payment protocol](https://x402.org). AI agents automatically pay micro-fees ($0.002–$0.010) per request in USDC on the Base network — no signup, no API keys, no rate limits.

## Quick Start

### Free endpoints (no payment):
```bash
# API health
curl http://43.157.206.248:4020/api/v1/free/health

# Fear & Greed Index
curl http://43.157.206.248:4020/api/v1/free/fear-greed

# ETH gas prices
curl http://43.157.206.248:4020/api/v1/free/gas
```

### Paid endpoints (x402 payment):
```bash
# Bitcoin price (returns 402 without payment)
curl http://43.157.206.248:4020/api/v1/price/bitcoin

# With x402-compatible wallet, payment is automatic
```

## 30+ Endpoints

### Market Data ($0.002-$0.005)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /api/v1/price/:coin_id` | $0.003 | Token price & 24h market data |
| `GET /api/v1/trending` | $0.005 | Currently trending crypto tokens |
| `GET /api/v1/market` | $0.003 | Global crypto market overview |
| `GET /api/v1/top-coins` | $0.005 | Top N coins by market cap |
| `GET /api/v1/search?q=` | $0.002 | Search coins by name/symbol |
| `GET /api/v1/defi` | $0.005 | DeFi protocols by TVL |
| `GET /api/v1/fear-greed` | $0.002 | Fear & Greed Index |
| `GET /api/v1/gas` | $0.002 | Multi-chain gas prices |

### DEX Intelligence ($0.002-$0.003)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /api/v1/dex/token/:chain/:address` | $0.003 | DEX trading pairs for token |
| `GET /api/v1/dex/pair/:chain/:pair_id` | $0.003 | DEX pair details |
| `GET /api/v1/dex/search?q=` | $0.002 | Search DEX tokens |
| `GET /api/v1/dex/trending` | $0.003 | Trending DEX tokens |
| `GET /api/v1/dex/boosted` | $0.002 | Top boosted tokens |

### DeFi Analytics ($0.002-$0.003)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /api/v1/protocols` | $0.003 | All DeFi protocols |
| `GET /api/v1/tvl/:protocol` | $0.002 | Protocol TVL |
| `GET /api/v1/chains` | $0.002 | Supported chains |

### Wallet Tracking ($0.003-$0.005)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /api/v1/wallet/:chain/:address` | $0.005 | Wallet native balance |
| `GET /api/v1/wallet/:chain/:address/transactions` | $0.005 | TX history |
| `GET /api/v1/wallet/:chain/:address/tokens` | $0.005 | ERC-20 transfers |
| `GET /api/v1/wallet/:chain/:address/internal` | $0.003 | Internal TXs |

### Contract & Token ($0.003)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /api/v1/contract/:chain/:address/abi` | $0.003 | Contract ABI + source |
| `GET /api/v1/token/:chain/:address/info` | $0.003 | Token info |

### Chain Data ($0.002-$0.003)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /api/v1/gas/:chain` | $0.002 | Etherscan gas tracker |
| `GET /api/v1/gas/multi` | $0.003 | Multi-chain gas |
| `GET /api/v1/block/:chain/latest` | $0.002 | Latest block |

### Premium ($0.003-$0.010)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /api/v1/whale/ethereum` | $0.010 | Whale alerts |
| `GET /api/v1/sentiment` | $0.005 | Market sentiment |
| `GET /api/v1/screener` | $0.005 | Token screener |
| `GET /api/v1/portfolio` | $0.008 | Multi-wallet tracker |
| `GET /api/v1/movers` | $0.003 | Top gainers/losers |
| `GET /api/v1/prices` | $0.002 | Batch prices |

### AI Vertical Micro-SaaS (v4.0, $0.005-$0.020) — POST
| Endpoint | Price | Description |
|----------|-------|-------------|
| `POST /api/v1/ai/legal-review` | $0.020 | AI legal contract review — risk, key terms, red flags |
| `POST /api/v1/ai/tax-id` | $0.015 | Indonesian PPh 21 tax estimator (UU HPP progressive) |
| `POST /api/v1/ai/invoice-ocr` | $0.010 | AI invoice/receipt parser — text to structured JSON |
| `POST /api/v1/ai/sentiment` | $0.005 | AI text sentiment + intent + entity extraction (multi-language) |

All AI endpoints powered by Xiaomi MiMo (mimo-v2-flash). Accept JSON body, return JSON response.

## How x402 Works

1. Client sends GET request to a paid endpoint
2. Server responds with `402 Payment Required` + payment details
3. Client's x402-compatible wallet automatically pays USDC on Base
4. Server verifies payment and returns the data

No API keys. No signup. No rate limits. Just pay per request.

## Tech Stack

- **Runtime:** Python 3.12 + FastAPI + Uvicorn
- **Payment:** x402 protocol (exact EVM, USDC on Base)
- **Auth:** Coinbase Developer Platform (CDP) Ed25519 JWT
- **Data:** CoinGecko, DexScreener, DefiLlama, Etherscan
- **Cache:** In-memory with configurable TTLs
- **Deployment:** Systemd + Nginx on Ubuntu

## Self-Host

```bash
git clone https://github.com/faisalnugroho/x402-crypto-api.git
cd x402-crypto-api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
export PAY_TO="0xYourBaseWalletAddress"
export CDP_API_KEY_ID="your-cdp-key-id"
export CDP_API_KEY_SECRET="your-cdp-key-secret"

# Run
python main.py
```

## MCP Server

For AI agents using MCP (Model Context Protocol):

```bash
cd mcp-server
pip install -r requirements.txt
python server.py
```

Provides 31 tools for Claude, Hermes, and other MCP-compatible agents.

## Python SDK

```bash
pip install x402-crypto
```

```python
from x402_crypto import X402Client

client = X402Client("http://43.157.206.248:4020")
price = await client.get_price("bitcoin")
```

## Pricing Revenue Model

| Scenario | Requests/day | Revenue/day | Revenue/month |
|----------|-------------|-------------|---------------|
| Low traffic | 100 | $0.30 | $9 |
| Medium traffic | 1,000 | $3.00 | $90 |
| High traffic | 10,000 | $30.00 | $900 |
| Viral | 100,000 | $300.00 | $9,000 |

Average price per request: ~$0.003

## License

MIT
