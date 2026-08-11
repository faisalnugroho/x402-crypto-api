# x402 Crypto Intelligence API

Pay-per-request crypto data & AI micro-SaaS on Base mainnet. AI agents pay in USDC via the x402 protocol — no API keys, no subscriptions, no accounts.

**Live on Base mainnet** · `https://api.cdp.coinbase.com` (CDP facilitator) · Builder Code: `bc_1g4yopsy`

---

## Pitch

The x402 protocol (Coinbase) enables HTTP-native payments: a client hits an endpoint, gets `402 Payment Required`, pays in USDC on Base, and retries with proof. **x402-crypto-api** is the production-grade seller implementation — 40+ endpoints serving real crypto market data, DEX analytics, and AI micro-services, all payable per request.

Built for the autonomous agent economy: any AI agent with a wallet can consume data without human onboarding.

### Why this matters

- **Zero friction**: No signups, no API keys, no billing dashboards. Payment is the auth.
- **Onchain attribution**: ERC-8021 builder-code `bc_1g4yopsy` embedded in every 402 response; CDP facilitator encodes it into settlement calldata.
- **Real revenue**: Every request earns USDC on Base mainnet. Not points, not testnet.

---

## Architecture

```
Client (AI Agent / app)
    │
    ▼ HTTP GET /api/v1/price/bitcoin
┌─────────────────────────────┐
│  x402-crypto-api (FastAPI)  │
│  • PaymentMiddlewareASGI    │──► 402 Payment Required (USDC, Base)
│  • RateLimiter              │    + PaymentRequirements
│  • Cache (TTL 5-30s)        │    + builder-code extension
└─────────────────────────────┘
    │
    ▼ x-payment-payload header (EIP-712 signed)
┌─────────────────────────────┐
│  CDP Facilitator (Coinbase) │
│  • Verify signature         │
│  • Settle USDC transfer     │──► Base mainnet
│  • Encode {a,s,w} Schema 2  │    (builder-code attribution)
└─────────────────────────────┘
    │
    ▼ 200 OK + data
Crypto data / DEX / AI services
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- CDP API Key (Coinbase Developer Platform) — for mainnet settlement
- Base mainnet RPC

### Install & Run

```bash
git clone https://github.com/faisalnugroho/x402-crypto-api.git
cd x402-crypto-api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt  # or: pip install fastapi uvicorn x402 httpx pyjwt cryptography

export CDP_API_KEY_ID="your-key-id"
export CDP_API_KEY_SECRET="your-key-secret"
export NETWORK="eip155:8453"

uvicorn main:app --host 0.0.0.0 --port 4020
```

### Test it

```bash
# Free endpoint (no payment)
curl http://localhost:4020/health

# Paid endpoint — will return 402
curl http://localhost:4020/api/v1/price/bitcoin

# With x402 client (pays automatically)
python x402_buyer_with_builder_code.py http://localhost:4020/api/v1/price/bitcoin
```

---

## Endpoints (40+)

| Category | Endpoint | Price |
|----------|----------|-------|
| **Market** | `/api/v1/price/:coin_id` | $0.003 |
| | `/api/v1/trending` | $0.005 |
| | `/api/v1/market` | $0.003 |
| | `/api/v1/top-coins` | $0.005 |
| | `/api/v1/fear-greed` | $0.002 |
| | `/api/v1/gas` | $0.002 |
| **DEX** | `/api/v1/dex/token/:chain/:address` | $0.003 |
| | `/api/v1/dex/pair/:chain/:pair_id` | $0.003 |
| | `/api/v1/dex/search` | $0.002 |
| | `/api/v1/dex/trending` | $0.003 |
| | `/api/v1/dex/boosted` | $0.002 |
| **DeFi** | `/api/v1/protocols` | $0.003 |
| | `/api/v1/tvl/:protocol` | $0.002 |
| **Wallet** | `/api/v1/wallet/:chain/:address` | $0.005 |
| | `/api/v1/wallet/:chain/:address/transactions` | $0.005 |
| | `/api/v1/wallet/:chain/:address/tokens` | $0.005 |
| **Contract** | `/api/v1/contract/:chain/:address/abi` | $0.003 |
| **Premium** | `/api/v1/whale/ethereum` | $0.010 |
| | `/api/v1/sentiment` | $0.005 |
| | `/api/v1/screener` | $0.005 |
| | `/api/v1/portfolio` | $0.008 |
| **AI SaaS** | `/api/v1/ai/legal-review` (POST) | $0.020 |
| | `/api/v1/ai/tax-id` (POST) | $0.015 |
| | `/api/v1/ai/invoice-ocr` (POST) | $0.010 |
| | `/api/v1/ai/sentiment` (POST) | $0.005 |

Full docs: `docs/API.md` · Quickstart: `docs/QUICKSTART.md`

---

## Builder Code & Attribution

This project declares **ERC-8021 builder-code** `bc_1g4yopsy` in every 402 response:

```json
{
  "extensions": {
    "builder-code": {
      "info": { "a": "bc_1g4yopsy" }
    }
  }
}
```

The CDP facilitator encodes `{a, s, w}` Schema 2 into the settlement transaction calldata, making revenue attribution verifiable onchain.

---

## Onchain Proof

- **Network**: Base mainnet (`eip155:8453`)
- **Asset**: USDC (exact scheme)
- **Facilitator**: Coinbase CDP (`api.cdp.coinbase.com`)
- **Seller**: `0xeb350f1692b16c8b7b02c66dedb76d018f6a9662`

*Transaction hashes from live testnet/mainnet runs will be listed here after audit.*

---

## Security

- `.gitignore` protects `.cdp_key`, `.cdp_secret`, `.env`, `venv/`
- Rate limiting: 30 req/min free, 300 req/min paid
- CORS restricted to necessary origins
- Input sanitization on all path/query params
- HMAC verification for partner webhooks (ShadowFeed)

---

## Data Sources

CoinGecko · DexScreener · DefiLlama · Etherscan · Public EVM RPCs

---

## License

MIT
