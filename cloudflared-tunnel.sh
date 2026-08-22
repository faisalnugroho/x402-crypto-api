#!/bin/bash
# Persistent cloudflared quick tunnel for x402 API
# URL changes on restart — check journalctl for new URL
exec /usr/local/bin/cloudflared tunnel --url http://localhost:4020 --no-autoupdate 2>&1
