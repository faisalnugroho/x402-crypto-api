# Quick Start for AI Agents

This guide shows AI agents how to use the x402 Crypto Intelligence API.

## Prerequisites

- An x402-compatible wallet with USDC on Base
- OR a Coinbase Developer Platform (CDP) account for x402 payments

## Step 1: Check the API

```bash
# Free endpoint — no payment needed
curl http://43.157.206.248:4020/

# Health check
curl http://43.157.206.248:4020/health
```

## Step 2: Make a Paid Request

```bash
# This will return 402 Payment Required
curl http://43.157.206.248:4020/api/v1/price/bitcoin
```

The response includes x402 payment details:

```json
{
  "x402Version": 1,
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:8453",
      "maxAmountRequired": "3000",
      "resource": "/api/v1/price/bitcoin",
      "payTo": "0xeb350f1692b16c8b7b02c66dedb76d018f6a9662"
    }
  ]
}
```

## Step 3: Pay with x402

Your x402-compatible wallet will automatically:

1. Parse the payment requirements
2. Sign and submit a USDC transfer on Base
3. Return the payment proof header
4. Retry the original request with the proof

## Using with Python

```python
import httpx
from x402.client import X402Client

# Initialize with your wallet
client = X402Client(
    wallet_private_key="your_private_key",
    network="base"
)

# Make a paid request
response = client.get("http://43.157.206.248:4020/api/v1/price/bitcoin")
data = response.json()
print(f"Bitcoin price: ${data['price']:,.2f}")
```

## Using with JavaScript

```javascript
import { X402Client } from 'x402-client';

const client = new X402Client({
  walletPrivateKey: 'your_private_key',
  network: 'base'
});

const response = await client.get('http://43.157.206.248:4020/api/v1/price/bitcoin');
const data = await response.json();
console.log(`Bitcoin price: $${data.price.toLocaleString()}`);
```

## Using with curl (manual payment)

```bash
# 1. Get payment requirements
PAYMENT_REQ=$(curl -s http://43.157.206.248:4020/api/v1/price/bitcoin)

# 2. Parse and pay manually (requires x402 wallet implementation)
# The x402 protocol handles this automatically with compatible clients

# 3. Include payment proof in headers
curl -H "X-PAYMENT: <base64-encoded-payment-proof>" \
  http://43.157.206.248:4020/api/v1/price/bitcoin
```

## Common Coin IDs

| Coin | ID |
|------|----|
| Bitcoin | `bitcoin` |
| Ethereum | `ethereum` |
| Solana | `solana` |
| Dogecoin | `dogecoin` |
| Cardano | `cardano` |
| XRP | `ripple` |
| Polkadot | `polkadot` |
| Avalanche | `avalanche-2` |
| Chainlink | `chainlink` |
| Uniswap | `uniswap` |

## Tips

- Use lowercase coin IDs (e.g., `bitcoin` not `Bitcoin`)
- Cache responses — prices don't change that fast
- The API has built-in rate limiting (6.5s between CoinGecko calls)
- For bulk data, use `/api/v1/top-coins?limit=100`
- Check `/api/v1/fear-greed` for market sentiment
