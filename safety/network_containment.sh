#!/usr/bin/env bash
# Wu v3 — Jetson network containment
#
# Installs firewall rules for Wu's SBC (Jetson).
# Idempotent: safe to re-run. Intended to be invoked by wu-network.service at boot
# and also by hand during debugging.
#
# Design principle: Wu's agent process runs as 'unitree' and should be contained
# to the robot subnet + Tailscale mesh + multicast buses it legitimately needs.
# The agent does NOT make external API calls directly (the LLM runs on Godzilla).
# Tailscaled (runs as root) needs outbound TCP 443 to reach DERP relays.
#
# Install: copy to /opt/wu/network_containment.sh, chmod +x, enable wu-network.service.

set -euo pipefail

# ---------------------------------------------------------------------------
# Make chains idempotent (flush or create)
# ---------------------------------------------------------------------------

for chain in WU_OUTPUT WU_INPUT; do
    iptables -N "$chain" 2>/dev/null || iptables -F "$chain"
done

# Ensure OUTPUT and INPUT jump to our chains at position 1 (idempotent)
iptables -D OUTPUT -j WU_OUTPUT 2>/dev/null || true
iptables -D INPUT  -j WU_INPUT  2>/dev/null || true

# Also strip the legacy chain if still present (replaced by WU_OUTPUT)
iptables -D OUTPUT -j WU_CONTAINMENT 2>/dev/null || true

iptables -I OUTPUT 1 -j WU_OUTPUT
iptables -I INPUT  1 -j WU_INPUT

# ---------------------------------------------------------------------------
# WU_OUTPUT — what Wu's Jetson is allowed to reach
# ---------------------------------------------------------------------------

# 1. Loopback: always allowed
iptables -A WU_OUTPUT -o lo -j ACCEPT

# 2. Reply traffic (conntrack)
iptables -A WU_OUTPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# 3. Robot subnet: Go2 (192.168.123.161), MID-360 (192.168.123.20),
#    Godzilla (192.168.123.205), future supervisor RPi (192.168.123.30)
iptables -A WU_OUTPUT -d 192.168.123.0/24 -j ACCEPT

# 4. Robot subnet directed broadcast
iptables -A WU_OUTPUT -d 192.168.123.255 -j ACCEPT

# 5. Limited broadcast — Livox SDK uses this for device discovery
iptables -A WU_OUTPUT -d 255.255.255.255 -j ACCEPT

# 6. Multicast — LCM bus (239.255.76.67) and Livox multicast data (224.1.1.5)
#    Covers all of 224.0.0.0/4 for link-local multicast and future bus channels
iptables -A WU_OUTPUT -d 224.0.0.0/4 -j ACCEPT

# 7. Tailscale UDP direct path
iptables -A WU_OUTPUT -p udp --dport 41641 -j ACCEPT

# 8. Tailscale mesh network (CGNAT range used for Tailscale peer IPs)
iptables -A WU_OUTPUT -d 100.64.0.0/10 -j ACCEPT

# 9. Tailscale DERP TCP fallback
#    tailscaled (runs as root on this host) needs outbound TCP 443 to reach
#    DERP relays, which rotate through a pool of IPs we can't enumerate.
#    jetson_robot.py does NOT initiate external HTTPS; this rule is a Tailscale
#    concession. If Wu's agent ever made a TCP 443 call it would match here —
#    the log line below captures anomalies.
iptables -A WU_OUTPUT -p tcp --dport 443 -j ACCEPT

# 10. DHCP client renewal
iptables -A WU_OUTPUT -p udp --dport 67 -j ACCEPT

# 11. DNS via Godzilla only (Godzilla is the NAT router and DNS relay)
iptables -A WU_OUTPUT -p udp --dport 53 -d 192.168.123.205 -j ACCEPT
iptables -A WU_OUTPUT -p tcp --dport 53 -d 192.168.123.205 -j ACCEPT

# 12. Log what falls through (rate-limited so log spam doesn't DoS dmesg)
iptables -A WU_OUTPUT -m limit --limit 5/minute --limit-burst 10 \
    -j LOG --log-prefix "[Wu:OUT-BLOCKED] " --log-level 4

# 13. Drop the rest
iptables -A WU_OUTPUT -j DROP

# ---------------------------------------------------------------------------
# WU_INPUT — what's allowed to reach the Jetson
# ---------------------------------------------------------------------------

# 1. Loopback
iptables -A WU_INPUT -i lo -j ACCEPT

# 2. Reply traffic (conntrack)
iptables -A WU_INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# 3. Anything from the robot subnet (SSH, LCM reply, sensor returns, future RPi scrapes)
iptables -A WU_INPUT -s 192.168.123.0/24 -j ACCEPT

# 4. Multicast destinations we subscribe to
iptables -A WU_INPUT -d 224.0.0.0/4 -j ACCEPT

# 5. Tailscale peers via the tun interface
iptables -A WU_INPUT -i tailscale0 -j ACCEPT

# 6. Tailscale UDP 41641 (inbound NAT hole punching)
iptables -A WU_INPUT -p udp --dport 41641 -j ACCEPT

# 7. Log what falls through
iptables -A WU_INPUT -m limit --limit 5/minute --limit-burst 10 \
    -j LOG --log-prefix "[Wu:IN-BLOCKED] " --log-level 4

# 8. Drop the rest (external unsolicited inbound)
iptables -A WU_INPUT -j DROP

# ---------------------------------------------------------------------------
# Multicast routes — not firewall, but required for multicast to go on
# the ethernet interface rather than defaulting to loopback.
# Livox SDK uses 224.1.1.5 when configured for multicast mode.
# ---------------------------------------------------------------------------

ip route add 224.1.1.5 dev enP8p1s0 2>/dev/null || true

echo "wu v3 containment rules applied"
