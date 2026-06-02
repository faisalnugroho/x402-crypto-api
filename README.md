# x402 Crypto Intelligence API

AI agent crypto data API — pay per request in USDC on Base. No API keys needed for clients.

## What is this?

An HTTP API that serves real-time cryptocurrency data from CoinGecko, protected by the [x402 payment protocol](https://x402.org). AI agents automatically pay micro-fees ($0.002–$0.005) per request in USDC on the Base network — no signup, no API keys, no rate limits.

## Quick Start

### For API consumers (AI agents):

```bash
# 1. Check the API is live
curl http://43.157.206.248:4020/

# 2. Get Bitcoin price (will return 402 Payment Required)
curl http://43.157.206.248:4020/api/v1/price/bitcoin

# 3. Pay with x402-compatible wallet and retry
# The x402 protocol handles payment automatically
```

### For developers (self-host):

```bash
git clone https://github.com/yourname/x402-crypto-api.git
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

## Endpoints

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

**Free endpoints:**
| Endpoint | Description |
|----------|-------------|
| `GET /` | Service info & endpoint list |
| `GET /health` | Health check |
| `GET /docs` | Swagger UI |

## How x402 Works

1. Client sends GET request to a paid endpoint
2. Server responds with `402 Payment Required` + payment details
3. Client's x402-compatible wallet automatically pays USDC on Base
4. Server verifies payment and returns the data

No API keys. No signup. No rate limits. Just pay per request.

## Architecture

```
Client (AI Agent)
    |
    | GET /api/v1/price/bitcoin
    v
x402 Crypto API (FastAPI + Uvicorn)
    |
    |--- PaymentMiddlewareASGI (x402 protocol)
    |       |
    |       |--- CDP Facilitator (Coinbase Developer Platform)
    |       |       Ed25519 JWT auth, Base MAINNET
    |       |
    |       |--- ExactEvmServerScheme (USDC on Base)
    |
    |--- CoinGecko API (free tier, 30 req/min)
    |--- Alternative.me (Fear & Greed)
    |--- Etherscan (Gas prices)
    |
    v
Response: JSON data
```

## Tech Stack

- **Runtime:** Python 3.12 + FastAPI + Uvicorn
- **Payment:** x402 protocol (exact EVM, USDC on Base)
- **Auth:** Coinbase Developer Platform (CDP) Ed25519 JWT
- **Data:** CoinGecko (free), Alternative.me, Etherscan
- **Deployment:** Systemd service on Ubuntu (Tencent Cloud)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PAY_TO` | `0xeb35...9662` | Wallet address to receive payments |
| `PORT` | `4020` | Server port |
| `CDP_API_KEY_ID` | — | Coinbase Developer Platform API key ID |
| `CDP_API_KEY_SECRET` | — | CDP API key secret (base64 Ed25519) |
| `NETWORK` | `eip155:8453` | Network (Base MAINNET) |

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
