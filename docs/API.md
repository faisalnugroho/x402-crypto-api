# API Documentation

Base URL: `http://43.157.206.248:4020`

All paid endpoints require x402 payment (USDC on Base). Free endpoints (`/`, `/health`, `/docs`) are accessible without payment.

---

## GET /

**Free** — Service information and endpoint list.

### Response

```json
{
  "service": "x402 Crypto Intelligence API",
  "version": "1.0.0",
  "payment": "USDC on Base (x402 protocol)",
  "pay_to": "0xeb350f1692b16c8b7b02c66dedb76d018f6a9662",
  "network": "eip155:8453",
  "endpoints": {
    "GET /api/v1/price/:coin_id": "$0.003 — Token price & market data",
    "GET /api/v1/trending": "$0.005 — Trending tokens",
    "GET /api/v1/market": "$0.003 — Global market overview",
    "GET /api/v1/top-coins": "$0.005 — Top coins by mcap",
    "GET /api/v1/search?q=": "$0.002 — Search coins",
    "GET /api/v1/defi": "$0.005 — DeFi protocols by TVL",
    "GET /api/v1/fear-greed": "$0.002 — Fear & Greed Index",
    "GET /api/v1/gas": "$0.002 — Multi-chain gas prices"
  },
  "docs": "/docs"
}
```

---

## GET /health

**Free** — Health check.

### Response

```json
{
  "status": "ok",
  "timestamp": 1780407570.222
}
```

---

## GET /api/v1/price/{coin_id}

**$0.003** — Get real-time price and 24h market data for any cryptocurrency.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `coin_id` | string | Yes | CoinGecko ID (lowercase): `bitcoin`, `ethereum`, `solana`, `dogecoin` |

### Response

```json
{
  "coin": "bitcoin",
  "currency": "usd",
  "price": 104832.15,
  "market_cap": 2073456789012,
  "volume_24h": 28934567890,
  "change_24h_pct": 2.34,
  "last_updated": 1780407500
}
```

### Example

```bash
# With x402 payment
curl http://43.157.206.248:4020/api/v1/price/bitcoin
curl http://43.157.206.248:4020/api/v1/price/ethereum
curl http://43.157.206.248:4020/api/v1/price/solana
curl http://43.157.206.248:4020/api/v1/price/dogecoin
```

---

## GET /api/v1/trending

**$0.005** — Get currently trending cryptocurrencies.

### Response

```json
{
  "trending": [
    {
      "id": "bitcoin",
      "name": "Bitcoin",
      "symbol": "BTC",
      "market_cap_rank": 1,
      "score": 0
    },
    {
      "id": "ethereum",
      "name": "Ethereum",
      "symbol": "ETH",
      "market_cap_rank": 2,
      "score": 1
    }
  ],
  "count": 10
}
```

---

## GET /api/v1/market

**$0.003** — Global cryptocurrency market overview.

### Response

```json
{
  "total_market_cap_usd": 3456789012345,
  "total_volume_24h_usd": 123456789012,
  "btc_dominance_pct": 52.34,
  "eth_dominance_pct": 17.89,
  "active_cryptos": 12345,
  "total_markets": 890,
  "market_cap_change_24h_pct": 1.23
}
```

---

## GET /api/v1/top-coins

**$0.005** — Get top cryptocurrencies ranked by market cap.

### Query Parameters

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | int | 20 | 100 | Number of coins to return |

### Response

```json
{
  "coins": [
    {
      "id": "bitcoin",
      "symbol": "btc",
      "name": "Bitcoin",
      "price": 104832.15,
      "market_cap": 2073456789012,
      "volume_24h": 28934567890,
      "change_1h": 0.12,
      "change_24h": 2.34,
      "change_7d": -1.23,
      "rank": 1
    }
  ],
  "count": 20
}
```

### Example

```bash
curl "http://43.157.206.248:4020/api/v1/top-coins?limit=10"
```

---

## GET /api/v1/search

**$0.002** — Search for cryptocurrencies by name or symbol.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (min 1 char) |

### Response

```json
{
  "query": "sol",
  "results": [
    {
      "id": "solana",
      "name": "Solana",
      "symbol": "SOL",
      "market_cap_rank": 5
    }
  ],
  "count": 1
}
```

### Example

```bash
curl "http://43.157.206.248:4020/api/v1/search?q=sol"
curl "http://43.157.206.248:4020/api/v1/search?q=doge"
```

---

## GET /api/v1/defi

**$0.005** — DeFi market data and top protocols by TVL.

### Response

```json
{
  "defi_market_cap_usd": "123456789012",
  "eth_market_cap_usd": "2073456789012",
  "trading_volume_24h_usd": "12345678901",
  "defi_to_defi_ratio": "0.12",
  "top_coins_count": 100,
  "top_defi": [
    {
      "id": "lido-dao",
      "name": "Lido DAO",
      "symbol": "LDO",
      "price": "0.00123",
      "change_24h": 3.45
    }
  ]
}
```

---

## GET /api/v1/fear-greed

**$0.002** — Crypto Fear & Greed Index with 7-day history.

### Response

```json
{
  "value": 72,
  "classification": "Greed",
  "history": [
    {"date": "1780358400", "value": 68, "label": "Greed"},
    {"date": "1780272000", "value": 65, "label": "Greed"},
    {"date": "1780185600", "value": 58, "label": "Neutral"}
  ]
}
```

### Classification Scale

| Value | Label |
|-------|-------|
| 0-24 | Extreme Fear |
| 25-49 | Fear |
| 50 | Neutral |
| 51-74 | Greed |
| 75-100 | Extreme Greed |

---

## GET /api/v1/gas

**$0.002** — Multi-chain gas price estimates.

### Response

```json
{
  "ethereum": {
    "low": "12",
    "standard": "15",
    "fast": "20"
  },
  "note": "Gas prices in Gwei. Other chains (Base, Polygon, BSC) are L2/Low-cost.",
  "base_estimate_usd": 0.001,
  "polygon_estimate_usd": 0.0001
}
```

---

## Error Responses

### 402 Payment Required

When calling a paid endpoint without x402 payment:

```json
{
  "x402Version": 1,
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:8453",
      "maxAmountRequired": "3000",
      "resource": "/api/v1/price/bitcoin",
      "description": "Token price & 24h market data (BTC, ETH, SOL, etc)",
      "mimeType": "application/json",
      "payTo": "0xeb350f1692b16c8b7b02c66dedb76d018f6a9662"
    }
  ],
  "payTo": "0xeb350f1692b16c8b7b02c66dedb76d018f6a9662"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["query", "q"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Rate Limiting

- CoinGecko free tier: ~30 requests/minute
- Built-in rate limiter: 1 request per 6.5 seconds to CoinGecko
- No client-side rate limiting (x402 payment IS the rate limiter)

## Data Sources

| Endpoint | Source | Update Frequency |
|----------|--------|-----------------|
| `/price` | CoinGecko | Real-time |
| `/trending` | CoinGecko | Real-time |
| `/market` | CoinGecko | Real-time |
| `/top-coins` | CoinGecko | Real-time |
| `/search` | CoinGecko | Real-time |
| `/defi` | CoinGecko | Real-time |
| `/fear-greed` | Alternative.me | Daily |
| `/gas` | Etherscan | Real-time |
