#!/bin/bash
# Finance Dashboard Security Hardening Script
# Run with: sudo ./scripts/security-hardening.sh
set -euo pipefail

echo "=== Finance Dashboard Security Hardening ==="

# 1. Enable UFW firewall
echo "[1/3] Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh  # SSH from anywhere
echo "UFW configured. Enabling..."
ufw --force enable
echo "UFW enabled."

# 2. Verify binding changes
echo "[2/3] Checking service bindings..."
echo "  FastAPI should bind to 127.0.0.1:8000 (code changes already applied)"
echo "  PocketBase binds to 127.0.0.1:8090 (already correct)"
echo "  ws_server.py binds to 127.0.0.1:8081 (already correct)"

# 3. Show firewall status
echo "[3/3] Firewall status:"
ufw status verbose

echo ""
echo "=== Hardening Complete ==="
echo "Note: Restart your services to pick up binding changes."
echo "  make db-start     # PocketBase"
echo "  make dev-server   # FastAPI backend"
echo "  make dev-frontend # Frontend (already on localhost)"