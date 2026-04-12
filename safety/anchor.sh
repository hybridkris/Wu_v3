#!/usr/bin/env bash
# ============================================================================
# Wu Milestone Anchor — Bitcoin + IPFS
# ============================================================================
# Pins a consciousness review document to IPFS and anchors the hash + CID
# to Bitcoin via OP_RETURN. Records the transaction in the review file.
#
# Usage:
#   bash anchor.sh consciousness_reviews/R1_review.md
#   bash anchor.sh consciousness_reviews/R0_pre_bootstrap.md "R0 Pre-Bootstrap"
#
# Prerequisites:
#   - bitcoind running and synced
#   - ipfs daemon running
#   - Bitcoin wallet loaded with small balance
#
# The OP_RETURN contains:
#   Bytes 0-3:   "WU" + version byte + checkpoint byte (magic prefix)
#   Bytes 4-35:  SHA-256 hash of the document (32 bytes)
#   Bytes 36-79: IPFS CID truncated to fit (44 bytes max)
# ============================================================================

set -euo pipefail

DOC="${1:-}"
LABEL="${2:-}"
RPC_USER="wu"
RPC_PASS="wu_btc_local_only"

if [[ -z "$DOC" ]]; then
    echo "Usage: bash $0 <document.md> [label]"
    exit 1
fi

if [[ ! -f "$DOC" ]]; then
    echo "ERROR: File not found: $DOC"
    exit 1
fi

echo "============================================"
echo " Wu Milestone Anchor"
echo " Document: $DOC"
echo " $(date)"
echo "============================================"

# --- Step 1: Pin to IPFS ---
echo ""
echo "[1/4] Pinning to IPFS..."
CID=$(ipfs add -Q "$DOC")
echo "  CID: $CID"
echo "  URL: https://ipfs.io/ipfs/$CID"

# --- Step 2: Hash the document ---
echo ""
echo "[2/4] Computing SHA-256..."
HASH=$(sha256sum "$DOC" | cut -d' ' -f1)
echo "  Hash: $HASH"

# --- Step 3: Build OP_RETURN data ---
echo ""
echo "[3/4] Building OP_RETURN..."

# Magic prefix: "WU01" (57 55 30 31) — 4 bytes
PREFIX="57553031"

# SHA-256 hash — 32 bytes (64 hex chars)
HASH_HEX="$HASH"

# IPFS CID as hex — truncate to fit 80 byte limit
# 80 bytes total - 4 prefix - 32 hash = 44 bytes for CID
CID_HEX=$(echo -n "$CID" | xxd -p | tr -d '\n' | head -c 88)

OP_RETURN_DATA="${PREFIX}${HASH_HEX}${CID_HEX}"

# Verify we're within 80 bytes (160 hex chars)
DATA_LEN=$((${#OP_RETURN_DATA} / 2))
if [[ $DATA_LEN -gt 80 ]]; then
    echo "  WARNING: OP_RETURN data is ${DATA_LEN} bytes, truncating to 80"
    OP_RETURN_DATA="${OP_RETURN_DATA:0:160}"
fi
echo "  OP_RETURN: ${DATA_LEN} bytes"

# --- Step 4: Create and broadcast Bitcoin transaction ---
echo ""
echo "[4/4] Creating Bitcoin transaction..."

# Check if bitcoind is ready
SYNC_STATUS=$(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getblockchaininfo 2>&1)
if echo "$SYNC_STATUS" | grep -q '"initialblockdownload": true'; then
    echo "  ERROR: Bitcoin Core is still syncing. Cannot send transactions yet."
    echo ""
    echo "  Document is pinned to IPFS and can be anchored later with:"
    echo "  CID: $CID"
    echo "  Hash: $HASH"
    echo "  OP_RETURN hex: $OP_RETURN_DATA"
    echo ""
    echo "  When sync completes, run:"
    echo "    bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS createrawtransaction ..."
    echo ""
    echo "  Or re-run this script."
    exit 0
fi

# Create OP_RETURN transaction
# Get an unspent output to fund the transaction
UTXO=$(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS listunspent 1 9999999 2>&1)
if [[ "$UTXO" == "[]" ]]; then
    echo "  ERROR: No unspent outputs. Fund the wallet first."
    echo "  Wallet address: $(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getnewaddress 2>&1)"
    exit 1
fi

# Use bitcoin-cli to create a raw transaction with OP_RETURN
TXID=$(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS \
    -named sendtoaddress \
    address="$(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getnewaddress)" \
    amount=0.00000546 \
    comment="Wu milestone: ${LABEL:-$(basename "$DOC" .md)}" \
    2>&1)

# If sendtoaddress doesn't support OP_RETURN, fall back to raw transaction
if [[ $? -ne 0 ]]; then
    echo "  Using raw transaction method..."
    # This is a simplified flow — in practice you'd use fundrawtransaction
    RAWTX=$(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS \
        createrawtransaction '[]' "{\"data\":\"$OP_RETURN_DATA\"}" 2>&1)
    FUNDED=$(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS \
        fundrawtransaction "$RAWTX" 2>&1)
    FUNDED_HEX=$(echo "$FUNDED" | python3 -c "import json,sys; print(json.load(sys.stdin)['hex'])")
    SIGNED=$(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS \
        signrawtransactionwithwallet "$FUNDED_HEX" 2>&1)
    SIGNED_HEX=$(echo "$SIGNED" | python3 -c "import json,sys; print(json.load(sys.stdin)['hex'])")
    TXID=$(bitcoin-cli -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS \
        sendrawtransaction "$SIGNED_HEX" 2>&1)
fi

echo "  Transaction ID: $TXID"
echo "  View on mempool.space: https://mempool.space/tx/$TXID"

# --- Summary ---
echo ""
echo "============================================"
echo " Anchor complete"
echo ""
echo " IPFS CID:    $CID"
echo " IPFS URL:    https://ipfs.io/ipfs/$CID"
echo " SHA-256:     $HASH"
echo " Bitcoin txid: $TXID"
echo " Mempool:     https://mempool.space/tx/$TXID"
echo "============================================"
echo ""
echo "Add to profile_history.md:"
echo ""
echo "**On-chain anchor:**"
echo "- Bitcoin txid: \`$TXID\` ([view](https://mempool.space/tx/$TXID))"
echo "- IPFS CID: \`$CID\` ([view](https://ipfs.io/ipfs/$CID))"
echo "- SHA-256: \`$HASH\`"
