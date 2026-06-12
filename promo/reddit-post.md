# Reddit Post — r/cryptocurrency or r/web3

## Title:
I built a crypto data API where AI agents pay per request in USDC — no API keys, no subscriptions

## Body:

Hey everyone,

I've been building an API specifically for AI agents that need crypto data. The idea is simple: instead of API keys and monthly subscriptions, agents pay per request using the x402 protocol (HTTP 402 + USDC on Base).

**What it does:**
- 30+ endpoints covering prices, DEX pairs, DeFi TVL, wallet tracking, whale alerts
- Data from CoinGecko, DexScreener, DefiLlama, Etherscan
- Starting at $0.002 per request
- Free tier with 3 endpoints to try

**Why x402?**
Traditional APIs require API keys, rate limits, and subscriptions. For autonomous AI agents, this is a pain. x402 lets agents pay programmatically — no keys, no accounts, just USDC micropayments.

**What's included:**
- Market data (prices, trending, Fear & Greed)
- DEX intelligence (pairs, liquidity, volume across all DEXes)
- DeFi analytics (TVL, protocols, chains)
- Wallet tracking (balances, TX history, ERC-20 transfers)
- Contract ABI + source code lookup
- MCP server for Claude/Hermes integration
- Python SDK (pip install x402-crypto)

**Try it free:**
```
curl http://43.157.206.248:4020/api/v1/free/fear-greed
```

**Docs:** http://43.157.206.248:4020/docs

Looking for feedback — what endpoints would you add? What pricing makes sense for your use case?

---

## Subreddits to post:
- r/cryptocurrency (2.5M members)
- r/defi (150K)
- r/web3 (100K)
- r/MachineLearning (3M) — focus on AI agent angle
- r/sideproject — focus on building aspect
- r/SideProjectIncome — focus on revenue model
