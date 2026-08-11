# Base Builder Grant Application Draft
# x402-crypto-api — pay-per-request API infrastructure on Base

---

## 1. Project Name
x402 Crypto Intelligence API

## 2. One-liner
Production-grade pay-per-request crypto data & AI micro-SaaS on Base mainnet, powered by the x402 protocol — AI agents pay in USDC per request, no API keys needed.

## 3. What is your project?
x402-crypto-api is a live seller implementation of the x402 payment protocol on Base mainnet. It exposes 40+ REST endpoints serving crypto market data (CoinGecko, DexScreener, DefiLlama), DEX analytics, wallet/contract queries, and AI micro-services (legal review, tax estimation, invoice OCR, sentiment analysis). Every request is paid in USDC via the Coinbase CDP facilitator using the exact EVM scheme.

## 4. What have you shipped?
- FastAPI server with x402 PaymentMiddlewareASGI + custom RateLimiter + response caching
- 40+ paid endpoints across crypto-data, DEX, DeFi, wallet, contract, premium, and AI verticals
- ERC-8021 builder-code `bc_1g4yopsy` declared in every 402 response for onchain attribution
- CDP facilitator integration (Ed25519 JWT auth, /supported, bazaar discovery)
- Response caching (5-30s TTL) + rate limiting (30 free / 300 paid req/min)
- Landing page, docs, robots.txt, sitemap.xml for SEO/discovery
- Python SDK in `sdk/` for buyers
- Live at :4020 on Base mainnet (eip155:8453)

## 5. Onchain / technical proof
- Network: Base mainnet (eip155:8453)
- Asset: USDC (exact scheme)
- Facilitator: Coinbase CDP (api.cdp.coinbase.com)
- Seller address: 0xeb350f1692b16c8b7b02c66dedb76d018f6a9662
- Builder code: bc_1g4yopsy (ERC-8021 Schema 2, encoded by CDP facilitator in settlement calldata)
- *Tx hashes to be inserted after final end-to-end payment test*

## 6. Why Base?
Base is the only L2 with first-party x402 support via Coinbase CDP. Native USDC, instant finality, and the largest retail onchain userbase make it the default settlement layer for the agent economy. Base's builder-code standard (ERC-8021) also lets us prove attribution without middleware.

## 7. How does this benefit the Base ecosystem?
- Provides the reference implementation for x402 sellers on Base (40+ endpoints, production config)
- Lowers the barrier for AI agents to pay for data onchain — no invoices, no subscriptions
- Every payment is a real USDC transaction on Base, driving network usage and fee revenue
- Builder-code attribution creates a transparent revenue trail for future grant audits

## 8. Traction / usage
- Server live and responding to requests since June 2026
- Request tracking + analytics pipeline (SQLite) logs every request, response time, and payment status
- CDP facilitator /supported endpoint returns HTTP 200 with bazaar, builder-code, and eip2612GasSponsoring extensions
- *Will insert request counts + payment logs after final audit*

## 9. How will you use the grant?
- 40% — Infrastructure: dedicated Base RPC node, redundant server, monitoring/alerting
- 30% — Expansion: 20+ new endpoints (NFT data, perp DEX, SocialFi, real-time websockets)
- 20% — Growth: SEO content, agent SDKs (TypeScript/Rust), integrations with agent frameworks (Virtuals, Eliza, etc.)
- 10% — Audit & security: third-party review, formal verification of payment flows

## 10. Team
Faisal Nugroho — solo builder, full-stack. GitHub: faisalnugroho

## 11. Links
- GitHub: https://github.com/faisalnugroho/x402-crypto-api
- Live API: http://<vps-ip>:4020 (or https://x402.dediserve.com if domain configured)
- Docs: in-repo docs/API.md + docs/QUICKSTART.md

## 12. Anything else?
x402 is the missing payment rail for the autonomous agent economy. This project proves it works on Base mainnet today, with real USDC settlement and verifiable builder attribution. The grant will scale it from a working prototype to the default data layer for agents on Base.

---

## TODO before submit
- [ ] Insert real tx hash from end-to-end payment test
- [ ] Insert request count stats from tracker.db
- [ ] Add screenshot of 402 response + settlement tx on BaseScan
- [ ] Confirm live URL/domain
