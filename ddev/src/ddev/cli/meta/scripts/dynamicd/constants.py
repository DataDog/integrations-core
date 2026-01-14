# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Constants for DynamicD."""

# LLM Configuration
# Using Sonnet for good balance of quality and speed. For complex integrations,
# consider using "claude-opus-4-20250514" for better reasoning.
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 16000
MAX_RETRIES = 3

# Rate limiting defaults
# Note: This is minimum per batch - script should send ALL dashboard metrics in each batch
DEFAULT_METRICS_PER_BATCH = 100  # Target metrics per batch (should cover all dashboard metrics)
DEFAULT_DURATION_SECONDS = 0  # 0 = run forever (continuous mode by default)
DEFAULT_BATCH_INTERVAL_SECONDS = 10  # Send every 10 seconds (realistic for monitoring)

# Scenarios available for simulation
SCENARIOS = {
    "healthy": "Normal operation with baseline metrics and minor variations",
    "degraded": "Performance issues: increased latency, higher resource usage, some errors",
    "incident": "Active incident: failures, saturation, alerts firing",
    "recovery": "System recovering from incident: metrics returning to normal",
    "peak_load": "High traffic period: elevated but healthy metrics",
    "maintenance": "Scheduled maintenance: some components offline or reduced capacity",
}

# Datadog API endpoints
DATADOG_SITES = {
    "datadoghq.com": "https://api.datadoghq.com",
    "us3.datadoghq.com": "https://api.us3.datadoghq.com",
    "us5.datadoghq.com": "https://api.us5.datadoghq.com",
    "datadoghq.eu": "https://api.datadoghq.eu",
    "ddog-gov.com": "https://api.ddog-gov.com",
    "ap1.datadoghq.com": "https://api.ap1.datadoghq.com",
}

# Output directory name
FAKE_DATA_DIR = "fake_data"
