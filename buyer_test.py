#!/usr/bin/env python3
"""
x402 Buyer — test payment against our own API.
Triggers Bazaar auto-indexing on first successful payment via CDP facilitator.
"""
import asyncio
import os
import sys
import httpx

from eth_account import Account
from x402 import x402Client, SchemeRegistration
from x402.http import x402HTTPClient, decode_payment_required_header
from x402.mechanisms.evm.exact import ExactEvmClientScheme

PRIVATE_KEY = os.environ.get("X402_PAYER_KEY", "0x940b84490b70097cff687198428e89cb7acdc3217eae111dd0159a02d2de73ab")
BASE_URL = os.environ.get("X402_BASE_URL", "https://civilization-jacket-released-desperate.trycloudflare.com")
NETWORK = "eip155:8453"  # Base mainnet


async def main():
    endpoint = sys.argv[1] if len(sys.argv) > 1 else "/api/v1/fear-greed"
    url = f"{BASE_URL}{endpoint}"

    account = Account.from_key(PRIVATE_KEY)
    print(f"Payer: {account.address}")
    print(f"Target: {url}")
    print()

    # Setup x402 client with exact EVM scheme
    scheme = ExactEvmClientScheme(signer=account)
    client = x402Client()
    client.register(NETWORK, scheme)
    http_client = x402HTTPClient(client)

    async with httpx.AsyncClient(timeout=30.0) as http:
        # Step 1: Initial request → expect 402
        print("Step 1: Initial request (expect 402)...")
        r1 = await http.get(url)
        print(f"  Status: {r1.status_code}")

        if r1.status_code != 402:
            print(f"  Unexpected status. Body: {r1.text[:300]}")
            return

        # Step 2: Parse payment requirements
        print("Step 2: Parsing payment requirements...")
        payment_required = http_client.get_payment_required_response(
            get_header=lambda h: r1.headers.get(h),
            body=r1.content,
        )
        print(f"  Version: {payment_required.x402_version}")
        if hasattr(payment_required, 'accepts'):
            for opt in payment_required.accepts:
                price = getattr(opt, 'max_amount', None) or getattr(opt, 'price', 'unknown')
                print(f"  Scheme: {opt.scheme}, Price: {price}, PayTo: {opt.pay_to}")

        # Step 3: Create payment payload
        print("Step 3: Creating payment payload...")
        payload = await http_client.create_payment_payload(payment_required)
        headers = http_client.encode_payment_signature_header(payload)
        print(f"  Payment header keys: {list(headers.keys())}")

        # Step 4: Retry with payment
        print("Step 4: Retrying with payment header...")
        r2 = await http.get(url, headers=headers)
        print(f"  Status: {r2.status_code}")

        if r2.status_code == 200:
            print()
            print("=== PAYMENT SUCCESS ===")
            print(f"Response: {r2.text[:500]}")
            # Check payment response header (settlement receipt)
            receipt = r2.headers.get("x-payment-response", "")
            if receipt:
                settle = http_client.get_payment_settle_response(
                    get_header=lambda h: r2.headers.get(h)
                )
                print(f"Settlement: success={settle.success}")
                if hasattr(settle, 'transaction'):
                    print(f"Tx: {settle.transaction}")
        else:
            print(f"  FAILED. Body: {r2.text[:500]}")
            # Try to parse settle error
            try:
                result = http_client.process_payment_result(
                    payload,
                    get_header=lambda h: r2.headers.get(h),
                    status=r2.status_code,
                )
                print(f"  Process result: {result}")
            except Exception as e:
                print(f"  Error parsing: {e}")


if __name__ == "__main__":
    asyncio.run(main())
