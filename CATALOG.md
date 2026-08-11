# x402 Crypto Intelligence API — Catalog & Status

Self-managed x402 seller (no Cloudflare dependency). Protocol-compatible
with the Cloudflare Monetization Gateway announced 2026-07-01: HTTP 402,
stablecoin (USDC) settlement on Base, peer-to-peer to seller wallet,
sub-cent pricing, builder-code attribution.

## Status (verified 2026-07-07)
- Seller process: LIVE (pid 3831066, started 2026-06-23)
- Location: /home/ubuntu/x402-crypto-api/main.py  (port 4020)
- Facilitator: CDP production (api.cdp.coinbase.com) — CDP key files present
- Network: eip155:8453 (Base)
- Settlement asset: USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)
- Seller wallet (payTo): 0xeb350f1692b16c8b7b02c66dedb76d018f6a9662
- Builder code (seller attribution, info.a): bc_1g4yopsy
- Live 402 handshake: VERIFIED — emits x402Version 2 with correct
  payTo / amount / asset / builder-code in `payment-required` header.

## Proof points (real tool output, 2026-07-07)
- `GET /api/v1/fear-greed` (no payment) -> HTTP 402, header decodes to:
  amount "2000" (= $0.002), asset USDC, network eip155:8453,
  extensions.builder-code.info.a = "bc_1g4yopsy"
- `GET /api/v1/free/fear-greed` (free tier) -> returns live data from
  https://api.alternative.me/fng/  (real external API, cached 120s)
- Handler code confirms real upstream calls (CoinGecko, DexScreener,
  DefiLlama, Etherscan, alternative.me, public RPCs) — NOT mocked.

## Paid endpoint catalog (35 paid + 3 free)
Prices are per-request, settled in USDC on Base.

Crypto-data ($0.002–$0.005):
- GET /api/v1/price/:coin_id            $0.003
- GET /api/v1/trending                  $0.005
- GET /api/v1/market                    $0.003
- GET /api/v1/top-coins                 $0.005
- GET /api/v1/search                    $0.002
- GET /api/v1/defi                      $0.005
- GET /api/v1/fear-greed                $0.002   <-- FLAGSHIP (cheapest, high demand)
- GET /api/v1/gas                       $0.002

DEX-data ($0.002–$0.003):
- GET /api/v1/dex/token/:chain/:address $0.003
- GET /api/v1/dex/pair/:chain/:pair_id  $0.003
- GET /api/v1/dex/search                $0.002
- GET /api/v1/dex/trending              $0.003
- GET /api/v1/dex/boosted               $0.002

DeFiLlama ($0.002–$0.003):
- GET /api/v1/protocols                 $0.003
- GET /api/v1/tvl/:protocol             $0.002
- GET /api/v1/chains                    $0.002

Wallet / Etherscan ($0.002–$0.005):
- GET /api/v1/wallet/:chain/:address                $0.005
- GET /api/v1/gas/multi                             $0.003
- GET /api/v1/wallet/:chain/:address/transactions   $0.005
- GET /api/v1/wallet/:chain/:address/tokens         $0.005
- GET /api/v1/wallet/:chain/:address/internal       $0.003
- GET /api/v1/contract/:chain/:address/abi          $0.003
- GET /api/v1/token/:chain/:address/info            $0.003
- GET /api/v1/gas/:chain                            $0.002
- GET /api/v1/block/:chain/latest                   $0.002

Premium ($0.005–$0.010):
- GET /api/v1/whale/ethereum         $0.010   <-- highest value
- GET /api/v1/sentiment              $0.005
- GET /api/v1/screener               $0.005
- GET /api/v1/ai/legal-review        (AI micro-SaaS, rate-limited)
- GET /api/v1/ai/tax-id
- GET /api/v1/ai/invoice-ocr
- GET /api/v1/ai/sentiment

Free (no payment, for onboarding/tests):
- GET /api/v1/free/health
- GET /api/v1/free/fear-greed
- GET /api/v1/free/gas

## Flagship recommendation
- Volume play: /api/v1/fear-greed @ $0.002 (cheapest, agents poll it often).
- Revenue play: /api/v1/whale/ethereum @ $0.010 (highest price, niche demand).
- Composite upsell (not yet built): /api/v1/brief — combines fear-greed +
  trending + gas into one call; propose $0.008 (below sum of parts, simpler
  for agents). Handler code ready to add in premium_endpoints.py.

## Buyer side (consuming external x402 resources)
- Buyer script: /tmp/x402-pay/x402_buyer_with_builder_code.py (verified
  end-to-end 2026-06-23 against mock seller; emits info.s = bc_1g4yopsy).
- Buyer hot wallet: 0xb6C78976Fb49f24efFBE5B584dDb5AbC062d3A07 (Base)
- BLOCKER: wallet not yet funded. Strategy A = send ~$3 ETH, swap above
  0.0001 ETH gas reserve to USDC via Paraswap, then pay $0.002/call.
- After funding, run:
    cd /tmp; export BUILDER_CODE=bc_1g4yopsy; export X402_PAYER_KEY=<keyfile>
    python3 /tmp/x402-pay/x402_buyer_with_builder_code.py \
      --url http://localhost:4020/api/v1/fear-greed --auto-swap \
      --swap-target 2.5 --verbose

## Position vs Cloudflare Monetization Gateway
- Cloudflare: managed edge, waitlist (not GA), USDC, Web Bot Auth identity.
- Us: self-hosted, LIVE now, same x402 protocol, CDP facilitator, our own
  builder code. No vendor lock-in; can later mirror to Cloudflare keeping
  the same builder-code attribution.
