# Draf Jawaban Form Base Builder Grant
# Form: https://www.buildergrants.xyz/builder-grant-form
# Project: x402 Crypto Intelligence API

---

## 1. Project Name

x402 Crypto Intelligence API

---

## 2. One-liner / Tagline

Pay-per-request crypto data & AI micro-SaaS on Base mainnet — AI agents pay in USDC via x402, no API keys needed.

---

## 3. Website / Demo URL

https://civilization-jacket-released-desperate.trycloudflare.com
(ganti dengan IP/domain publik setelah deploy)

Health check: https://civilization-jacket-released-desperate.trycloudflare.com/health
Docs: https://civilization-jacket-released-desperate.trycloudflare.com/docs

---

## 4. Problem

The autonomous agent economy needs infrastructure for machines to pay machines. Today, AI agents cannot consume most APIs because they require human onboarding: email signup, credit card, API key management, billing dashboards.

x402 solves the payment layer, but there are almost no production-grade sellers. Most x402 examples are "hello world" toys with no real data, no revenue, and no onchain attribution.

---

## 5. What is built

A production x402 seller on Base mainnet with 40+ paid endpoints serving real crypto market data, DEX analytics, and AI micro-services.

Key components:

1. **Payment middleware** (FastAPI): Returns HTTP 402 with PaymentRequirements (USDC, Base, exact scheme). Verified via CDP facilitator.
2. **Data layer**: CoinGecko, DexScreener, DefiLlama, Etherscan — real market data, not mocks.
3. **AI micro-SaaS**: Legal contract review, Indonesian tax calculator, invoice OCR, sentiment analysis — vertical AI services payable per request.
4. **Builder-code attribution**: ERC-8021 builder-code `bc_1g4yopsy` embedded in every 402 response; CDP encodes it into settlement calldata.
5. **Rate limiting & caching**: 30 req/min free tier, 300 req/min paid, TTL-based response caching.

Live seller address: `0xeb350f1692b16c8b7b02c66dedb76d018f6a9662`
Network: Base mainnet (eip155:8453)
Facilitator: Coinbase CDP (api.cdp.coinbase.com)

---

## 6. Traction / Onchain Proof

- Seller live on Base mainnet since June 2026
- 40+ endpoints across 6 categories
- CDP facilitator integration verified (HTTP 200 /supported)
- Builder-code `bc_1g4yopsy` declared in all 402 responses
- **Real onchain payment verified 2026-08-17**: buyer paid $0.002 USDC for `/api/v1/gas`, settled by CDP facilitator on Base mainnet
  - Settlement tx: `0x8f0a77ea6bab61c7a38be043beba914863ebe7ddaaaeb4ae68b9362e8676a66d`
  - Swap tx (buyer funded, ETH→USDC): `0x69217dda2eecabb83677d357117633bac7cb1ba815c363abcfd3315f8e1af289`
  - Payer: `0xb6C78976Fb49f24efFBE5B584dDb5AbC062d3A07` (Base mainnet)
  - Seller received: `0xeb350f1692b16c8b7b02c66dedb76d018f6a9662`

---

## 7. Team

Faisal Nugroho — solo builder, Indonesia.
GitHub: @faisalnugroho
Active on Base since 2025. Multiple repos: agentkit, onchainkit, defi-agents, developer-toolkit, basenames.

---

## 8. How will you use the grant?

$5,000 allocation:

- **$2,000**: Infrastructure & hosting (VPS, RPC, monitoring, 12 months)
- **$1,500**: Marketing & distribution (directories, agent SDK docs, demo video)
- **$1,000**: Data source costs (premium API tiers for higher rate limits)
- **$500**: Legal & compliance (terms of service, privacy policy for paid API)

Milestones:
- Month 1: 10,000 paid requests, 3 external integrators
- Month 2: 50,000 paid requests, $500 USDC revenue
- Month 3: 100,000 paid requests, profitable unit economics

---

## 9. Why Base?

Base is the only L2 with native x402 support via Coinbase CDP. The facilitator handles settlement, gas sponsoring, and builder-code attribution out of the box. No other chain has this stack.

Building on Base means:
- USDC settlements with sub-cent fees
- Native Coinbase distribution (bazaar discovery)
- ERC-8021 builder-code attribution for retroactive funding

---

## 10. Anything else?

This is not a speculative project. The seller is live, the facilitator is connected, and the builder code is embedded. The grant accelerates infrastructure hardening and go-to-market, not R&D.

---

## Catatan Internal (jangan di-copy ke form)

- [x] Ganti YOUR_VPS_IP dengan IP publik setelah deploy
- [x] Tambah tx hash setelah real payment test
- [x] Screenshot /docs dan /health kalau form ada field upload
- [ ] Cek deadline form — tweet bilang "rolling basis"
