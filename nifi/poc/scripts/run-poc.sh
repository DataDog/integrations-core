#!/usr/bin/env bash
# ABOUTME: End-to-end PoC runner: starts NiFi in Docker, creates test flows, collects all metrics.
# ABOUTME: Run from the poc/ directory. Saves API responses to responses/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
POC_DIR="$(dirname "$SCRIPT_DIR")"

cd "$POC_DIR"

echo "=== NiFi Agent Integration PoC ==="
echo ""

# Step 1: Start NiFi
echo "Step 1: Starting NiFi 2.8.0 via Docker Compose..."
docker compose up -d
echo ""

# Step 2: Wait for NiFi to be ready
echo "Step 2: Waiting for NiFi to become ready (this takes 60-90s on first start)..."
"$SCRIPT_DIR/wait-for-nifi.sh"
echo ""

# Step 3: Create test flows
echo "Step 3: Creating test flows..."
"$SCRIPT_DIR/setup-flow.sh"
echo ""

# Step 4: Wait for data to flow
echo "Step 4: Waiting 30 seconds for data to flow and bulletins to appear..."
sleep 30
echo ""

# Step 5: Collect metrics
echo "Step 5: Collecting all monitoring endpoint responses..."
"$SCRIPT_DIR/collect-metrics.sh" "$POC_DIR/responses"
echo ""

echo "=== PoC Complete ==="
echo ""
echo "To explore further:"
echo "  NiFi UI: https://localhost:8443/nifi/ (admin / ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB)"
echo "  API responses: ${POC_DIR}/responses/"
echo ""
echo "To tear down:"
echo "  cd ${POC_DIR} && docker compose down -v"
