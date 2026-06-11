"""
Etherscan API endpoints — wallet history, token balances, contract ABI.
Requires Etherscan API key (free tier: 5 req/sec).
"""
from fastapi import APIRouter, Query
import httpx
import os
import time
from cache import cached

router = APIRouter(prefix="/api/v1", tags=["etherscan"])

# Load API key
_key_path = os.path.join(os.path.dirname(__file__), ".etherscan_key")
try:
    with open(_key_path) as f:
        ETHERSCAN_KEY = f.read().strip()
except Exception:
    ETHERSCAN_KEY = ""

# Etherscan V2 — single base URL, chain ID parameter
ETHERSCAN_V2_BASE = "https://api.etherscan.io/v2/api"

# Chain name → chainid
CHAIN_IDS = {
    "ethereum": 1, "eth": 1,
    "bsc": 56, "bnb": 56,
    "polygon": 137, "matic": 137,
    "arbitrum": 42161, "arb": 42161,
    "optimism": 10, "op": 10,
    "base": 8453,
    "avalanche": 43114, "avax": 43114,
    "fantom": 250, "ftm": 250,
    "gnosis": 100,
    "linea": 59144,
    "scroll": 534352,
    "zksync": 324,
    "mantle": 5000,
    "blast": 81457,
}

# Native token symbols per chain
CHAIN_NATIVE = {
    "ethereum": "ETH", "bsc": "BNB", "polygon": "MATIC",
    "arbitrum": "ETH", "optimism": "ETH", "base": "ETH",
    "avalanche": "AVAX", "fantom": "FTM", "gnosis": "xDAI",
    "linea": "ETH", "scroll": "ETH", "zksync": "ETH",
    "mantle": "MTL", "blast": "ETH",
}


async def _etherscan_get(chain: str, params: dict) -> dict:
    """Make authenticated Etherscan V2 API call."""
    chain_lower = chain.lower()
    chain_id = CHAIN_IDS.get(chain_lower)
    if not chain_id:
        return {"error": f"Chain '{chain}' not supported", "supported": [k for k in CHAIN_IDS if CHAIN_IDS[k] < 10000]}
    if not ETHERSCAN_KEY:
        return {"error": "Etherscan API key not configured"}

    params["chainid"] = str(chain_id)
    params["apikey"] = ETHERSCAN_KEY
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(ETHERSCAN_V2_BASE, params=params)
        if r.status_code != 200:
            return {"error": f"Etherscan returned {r.status_code}"}
        data = r.json()
        if data.get("status") == "0" and data.get("message") != "OK":
            return {"error": data.get("result", "Unknown Etherscan error")}
        return data


# ============================================================
# WALLET TRANSACTION HISTORY
# ============================================================

@cached(30, "eth_txlist")
@router.get("/wallet/{chain}/{address}/transactions")
async def wallet_transactions(
    chain: str,
    address: str,
    page: int = Query(default=1, ge=1),
    offset: int = Query(default=20, ge=1, le=100),
):
    """
    Get normal transaction history for a wallet.
    Returns last `offset` transactions (default 20).
    """
    data = await _etherscan_get(chain, {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": "0",
        "endblock": "99999999",
        "page": str(page),
        "offset": str(offset),
        "sort": "desc",
    })
    if "error" in data:
        return data

    txs = data.get("result", [])
    native = CHAIN_NATIVE.get(chain.lower(), "ETH")
    results = []
    for tx in txs[:offset]:
        value_wei = int(tx.get("value", "0"))
        value_native = value_wei / 10**18
        results.append({
            "hash": tx.get("hash"),
            "block": tx.get("blockNumber"),
            "timestamp": tx.get("timeStamp"),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value": round(value_native, 6),
            "value_wei": tx.get("value"),
            "symbol": native,
            "gas_used": tx.get("gasUsed"),
            "gas_price": tx.get("gasPrice"),
            "status": "success" if tx.get("txreceipt_status") == "1" else "failed",
            "method": tx.get("input", "")[:10] if tx.get("input") and tx.get("input") != "0x" else "transfer",
            "is_error": tx.get("isError") == "1",
        })

    return {
        "chain": chain.lower(),
        "address": address,
        "transactions": results,
        "count": len(results),
        "page": page,
        "source": "etherscan",
    }


# ============================================================
# TOKEN TRANSFERS (ERC-20)
# ============================================================

@cached(30, "eth_tokentx")
@router.get("/wallet/{chain}/{address}/tokens")
async def wallet_token_transfers(
    chain: str,
    address: str,
    page: int = Query(default=1, ge=1),
    offset: int = Query(default=20, ge=1, le=100),
):
    """
    Get ERC-20 token transfer history for a wallet.
    Shows tokens received/sent.
    """
    data = await _etherscan_get(chain, {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "page": str(page),
        "offset": str(offset),
        "sort": "desc",
    })
    if "error" in data:
        return data

    txs = data.get("result", [])
    results = []
    for tx in txs[:offset]:
        decimals = int(tx.get("tokenDecimal", "18"))
        value_raw = int(tx.get("value", "0"))
        value = value_raw / 10**decimals if decimals > 0 else value_raw
        results.append({
            "hash": tx.get("hash"),
            "block": tx.get("blockNumber"),
            "timestamp": tx.get("timeStamp"),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "token_name": tx.get("tokenName"),
            "token_symbol": tx.get("tokenSymbol"),
            "token_address": tx.get("contractAddress"),
            "token_decimal": decimals,
            "value": round(value, 6),
            "value_raw": tx.get("value"),
            "method": "receive" if tx.get("to", "").lower() == address.lower() else "send",
        })

    return {
        "chain": chain.lower(),
        "address": address,
        "token_transfers": results,
        "count": len(results),
        "page": page,
        "source": "etherscan",
    }


# ============================================================
# INTERNAL TRANSACTIONS
# ============================================================

@cached(60, "eth_internal")
@router.get("/wallet/{chain}/{address}/internal")
async def wallet_internal_txs(
    chain: str,
    address: str,
    page: int = Query(default=1, ge=1),
    offset: int = Query(default=20, ge=1, le=100),
):
    """
    Get internal transactions (contract calls) for a wallet.
    """
    data = await _etherscan_get(chain, {
        "module": "account",
        "action": "txlistinternal",
        "address": address,
        "startblock": "0",
        "endblock": "99999999",
        "page": str(page),
        "offset": str(offset),
        "sort": "desc",
    })
    if "error" in data:
        return data

    txs = data.get("result", [])
    native = CHAIN_NATIVE.get(chain.lower(), "ETH")
    results = []
    for tx in txs[:offset]:
        value_wei = int(tx.get("value", "0"))
        value_native = value_wei / 10**18
        results.append({
            "hash": tx.get("hash"),
            "block": tx.get("blockNumber"),
            "timestamp": tx.get("timeStamp"),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value": round(value_native, 6),
            "symbol": native,
            "type": tx.get("type"),
            "gas": tx.get("gas"),
            "gas_used": tx.get("gasUsed"),
            "status": "success" if tx.get("isError") == "0" else "failed",
        })

    return {
        "chain": chain.lower(),
        "address": address,
        "internal_transactions": results,
        "count": len(results),
        "page": page,
        "source": "etherscan",
    }


# ============================================================
# CONTRACT ABI
# ============================================================

@cached(3600, "eth_abi")
@router.get("/contract/{chain}/{address}/abi")
async def contract_abi(chain: str, address: str):
    """
    Get smart contract ABI and source code.
    """
    data = await _etherscan_get(chain, {
        "module": "contract",
        "action": "getabi",
        "address": address,
    })
    if "error" in data:
        return data

    abi_str = data.get("result", "")
    import json as _json
    try:
        abi = _json.loads(abi_str) if abi_str and abi_str != "Contract source code not verified" else None
    except Exception:
        abi = None

    # Also try to get source code
    data2 = await _etherscan_get(chain, {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
    })
    source_info = {}
    if "error" not in data2 and data2.get("result"):
        src = data2["result"][0] if isinstance(data2["result"], list) else {}
        source_info = {
            "contract_name": src.get("ContractName"),
            "compiler": src.get("CompilerVersion"),
            "optimization": src.get("OptimizationUsed"),
            "verified": src.get("ABI") != "Contract source code not verified",
            "license": src.get("LicenseType"),
        }

    return {
        "chain": chain.lower(),
        "address": address,
        "abi": abi,
        "abi_length": len(abi) if abi else 0,
        "functions": [f.get("name") for f in abi if f.get("type") == "function"] if abi else [],
        "source": source_info,
        "source_api": "etherscan",
    }


# ============================================================
# TOKEN INFO
# ============================================================

@cached(300, "eth_tokeninfo")
@router.get("/token/{chain}/address/{address}/info")
async def token_info(chain: str, address: str):
    """
    Get ERC-20 token info (name, symbol, total supply, holders estimate).
    """
    # Get token info via contract call
    data = await _etherscan_get(chain, {
        "module": "token",
        "action": "tokeninfo",
        "contractaddress": address,
    })
    if "error" in data:
        # Fallback: try to get from source code
        return {
            "chain": chain.lower(),
            "address": address,
            "error": data["error"],
            "hint": "Token may not be verified on Etherscan",
        }

    tokens = data.get("result", [])
    if not tokens:
        return {"error": "Token not found", "chain": chain, "address": address}

    t = tokens[0] if isinstance(tokens, list) else tokens
    return {
        "chain": chain.lower(),
        "address": address,
        "name": t.get("tokenName"),
        "symbol": t.get("symbol"),
        "decimal": t.get("divisor"),
        "total_supply": t.get("totalSupply"),
        "holders": t.get("tokenHolders"),
        "source": "etherscan",
    }


# ============================================================
# ENHANCED GAS (Etherscan Gas Tracker)
# ============================================================

@cached(15, "etherscan_gas")
@router.get("/gas/{chain}")
async def etherscan_gas(chain: str):
    """
    Get gas prices from Etherscan Gas Tracker (more accurate than public RPC).
    Falls back to public RPC for chains without free Etherscan gas access.
    """
    data = await _etherscan_get(chain, {
        "module": "gastracker",
        "action": "gasoracle",
    })
    # If Etherscan fails (pro-only chain), fallback to RPC
    if "error" in data:
        from endpoints import _get_gas_from_rpc
        rpc_data = await _get_gas_from_rpc(chain)
        if rpc_data:
            rpc_data["source"] = "public-rpc-fallback"
            rpc_data["chain"] = chain.lower()
            rpc_data["etherscan_error"] = data.get("error")
            return rpc_data
        return data

    result = data.get("result", {})
    return {
        "chain": chain.lower(),
        "low": result.get("SafeGasPrice"),
        "standard": result.get("ProposeGasPrice"),
        "fast": result.get("FastGasPrice"),
        "base_fee": result.get("suggestBaseFee"),
        "unit": "Gwei",
        "source": "etherscan-gas-tracker",
    }


# ============================================================
# BLOCK NUMBER (for sync status)
# ============================================================

@cached(5, "eth_blocknum")
@router.get("/block/{chain}/latest")
async def latest_block(chain: str):
    """Get latest block number and timestamp."""
    data = await _etherscan_get(chain, {
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": str(int(time.time())),
        "closest": "before",
    })
    if "error" in data:
        return data
    return {
        "chain": chain.lower(),
        "latest_block": int(data.get("result", 0)),
        "source": "etherscan",
    }
