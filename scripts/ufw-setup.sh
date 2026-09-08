#!/bin/bash
# ufw-setup.sh — Enable firewall with secure defaults
# Run with: sudo ./scripts/ufw-setup.sh
set -euo pipefail

echo "=== Configuring ufw firewall ==="

# Default policies
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow SSH
ufw allow 22/tcp comment 'SSH'

# Allow Plex
ufw allow 32400/tcp comment 'Plex'

# Allow Syncthing
ufw allow 22000/tcp comment 'Syncthing'

# Allow Hermes dashboards (local network only)
ufw allow from 127.0.0.1 to any port 3000 proto tcp comment 'Hermes dashboards (localhost)'
ufw allow from 127.0.0.1 to any port 8000 proto tcp comment 'Finance Dashboard API (localhost)'
ufw allow from 127.0.0.1 to any port 9123 proto tcp comment 'Agent Town HTTP (localhost)'
ufw allow from 127.0.0.1 to any port 9124 proto tcp comment 'Agent Town WS (localhost)'
ufw allow from 127.0.0.1 to any port 5173 proto tcp comment 'Vite dev (localhost)'
ufw allow from 127.0.0.1 to any port 3001 proto tcp comment 'Vite alt (localhost)'
ufw allow from 127.0.0.1 to any port 3002 proto tcp comment 'Vite alt2 (localhost)'
ufw allow from 127.0.0.1 to any port 11434 proto tcp comment 'Ollama (localhost)'
ufw allow from 127.0.0.1 to any port 8384 proto tcp comment 'Syncthing GUI (localhost)'
ufw allow from 127.0.0.1 to any port 631 proto tcp comment 'CUPS (localhost)'
ufw allow from 127.0.0.1 to any port 9222 proto tcp comment 'Chrome DevTools (localhost)'
ufw allow from 127.0.0.1 to any port 9223 proto tcp comment 'Chrome DevTools (localhost)'

# Enable
ufw --force enable

echo ""
echo "=== ufw status ==="
ufw status verbose

echo ""
echo "=== Current listening ports ==="
ss -tlnp | grep -v "127.0.0.1\|::1\|192.168"

echo ""
echo "⚠️  WARNING: Docker containers bypass ufw rules!"
echo "   Portainer (0.0.0.0:8000, 0.0.0.0:9443) is exposed."
echo "   To fix, either:"
echo "     1. Restart Portainer with '127.0.0.1:8000:8000' binding"
echo "     2. Add iptables rules to restrict Docker port forwarding"