#!/usr/bin/env python3
"""
Submit x402 Crypto API to multiple directories.
Run: python3 submit_directories.py
"""
import json
import os

API_INFO = {
    "name": "x402 Crypto Intelligence API",
    "description": "AI agent crypto data API — pay per request in USDC on Base. 30+ endpoints covering prices, DEX, DeFi, wallets, whale alerts. No API keys needed.",
    "url": "http://43.157.206.248:4020",
    "docs": "http://43.157.206.248:4020/docs",
    "github": "https://github.com/faisalnugroho/x402-crypto-api",
    "category": "Cryptocurrency",
    "tags": ["crypto", "defi", "blockchain", "ai-agent", "x402", "usdc", "base", "api"],
    "pricing": "Pay per request ($0.002-$0.010 in USDC)",
    "auth": "x402 protocol (no API keys)",
    "endpoints": 31,
    "free_tier": True,
}

# Directories to submit to
DIRECTORIES = [
    {
        "name": "Public APIs (GitHub)",
        "url": "https://github.com/public-apis/public-apis",
        "action": "Fork → Add entry to README → PR",
        "category": "Cryptocurrency",
        "format": "| [x402 Crypto API](http://43.157.206.248:4020) | AI agent crypto data API, pay per request in USDC on Base | `x402` |",
    },
    {
        "name": "RapidAPI",
        "url": "https://rapidapi.com/provider",
        "action": "Upload OpenAPI spec at /home/ubuntu/x402-crypto-api/openapi.json",
        "note": "User must click Publish from browser",
    },
    {
        "name": "api.market",
        "url": "https://api.market",
        "action": "Submit via website form",
    },
    {
        "name": "APILayer Marketplace",
        "url": "https://marketplace.apilayer.com",
        "action": "Submit via marketplace form",
    },
    {
        "name": "APIs.guru",
        "url": "https://github.com/APIs-guru/openapi-directory",
        "action": "Fork → Add OpenAPI spec → PR",
    },
    {
        "name": "x402 Bazaar (Coinbase)",
        "url": "https://x402.org/bazaar",
        "action": "Auto-indexed on first successful x402 payment through CDP Facilitator",
        "note": "Coinbase monitors live payments and adds services automatically",
    },
    {
        "name": "ShadowFeed Marketplace",
        "url": "https://shadowfeed.app",
        "action": "Register as provider → Submit feed URL",
        "note": "Bitcoin L2 (Stacks), 97% revenue share",
    },
    {
        "name": "MCP Hub",
        "url": "https://github.com/modelcontextprotocol/servers",
        "action": "Fork → Add MCP server entry → PR",
        "note": "For the MCP server at mcp-server/",
    },
    {
        "name": "Free for Dev",
        "url": "https://github.com/ripienaar/free-for-dev",
        "action": "Fork → Add to APIs section → PR",
        "note": "Highlight free tier endpoints",
    },
    {
        "name": "API List",
        "url": "https://github.com/abhishekbanthije/Awesome-APIs",
        "action": "Fork → Add entry → PR",
    },
]

print("=" * 60)
print("x402 Crypto API — Directory Submission Guide")
print("=" * 60)
print()
print(f"API: {API_INFO['name']}")
print(f"URL: {API_INFO['url']}")
print(f"Docs: {API_INFO['docs']}")
print(f"GitHub: {API_INFO['github']}")
print(f"Endpoints: {API_INFO['endpoints']}")
print()

for i, d in enumerate(DIRECTORIES, 1):
    print(f"{i}. {d['name']}")
    print(f"   URL: {d['url']}")
    print(f"   Action: {d['action']}")
    if 'note' in d:
        print(f"   Note: {d['note']}")
    if 'format' in d:
        print(f"   Format: {d['format']}")
    print()

print("=" * 60)
print("IMMEDIATE ACTIONS (can do now):")
print("=" * 60)
print()
print("1. Fork public-apis/public-apis → Add entry → PR")
print("2. Fork APIs-guru/openapi-directory → Add spec → PR")
print("3. Fork modelcontextprotocol/servers → Add MCP entry → PR")
print("4. Fork ripienaar/free-for-dev → Add entry → PR")
print()
print("USER ACTION NEEDED:")
print("1. RapidAPI: User must click 'Publish' from browser")
print("2. x402 Bazaar: Need first real x402 payment to trigger indexing")
print("3. ShadowFeed: Need Xverse wallet registration")
print()
