# DynamicD

Generate realistic fake telemetry data for Datadog integrations using AI.

DynamicD uses Claude to analyze an integration's metrics, service checks, and dashboards, then generates a Python script that simulates realistic, scenario-aware data.

## Setup

### Required: Anthropic API Key (for script generation)

```bash
# Option 1: Environment variable
export ANTHROPIC_API_KEY="your-anthropic-key"

# Option 2: ddev config
ddev config set dynamicd.llm_api_key "your-anthropic-key"
```

### Required: Datadog API Key (for sending data)

```bash
ddev config set orgs.<your-org>.api_key "your-dd-api-key"
```

### Optional: Datadog App Key (for org name validation)

```bash
ddev config set orgs.<your-org>.app_key "your-dd-app-key"
```

### Optional: Datadog Site (for non-US users)

```bash
# Default is datadoghq.com (US1)
ddev config set orgs.<your-org>.site datadoghq.eu      # EU
ddev config set orgs.<your-org>.site us3.datadoghq.com # US3
ddev config set orgs.<your-org>.site us5.datadoghq.com # US5
ddev config set orgs.<your-org>.site ap1.datadoghq.com # AP1
```

## Usage

```bash
# Interactive scenario selection
ddev meta scripts dynamicd <integration>

# Specific scenario
ddev meta scripts dynamicd celery --scenario incident

# Save script for later use
ddev meta scripts dynamicd redis --scenario healthy --save

# Preview without executing
ddev meta scripts dynamicd postgres --show-only

# Custom duration (default: run forever)
ddev meta scripts dynamicd kafka --duration 300
```

## Scenarios

| Scenario | Description |
|----------|-------------|
| `healthy` | Normal operation with baseline metrics. |
| `degraded` | Performance issues, increased latency, some errors. |
| `incident` | Active incident with failures and alerts. |
| `recovery` | System recovering, metrics returning to normal. |
| `peak_load` | High traffic, elevated but healthy metrics. |
| `maintenance` | Scheduled maintenance, reduced capacity. |

## What Gets Generated

DynamicD creates scripts that send:

- **Metrics**: All dashboard metrics with realistic, correlated values
- **Logs**: Scenario-appropriate log messages (INFO/WARN/ERROR)
- **Service Checks**: Health status matching the scenario (if integration defines them)
- **Events**: Significant state changes (incidents, recoveries)

All telemetry is tagged with `env:dynamicd` for easy filtering in Datadog.

## How It Works

1. **Context Building**: Reads integration metadata, metrics, dashboards, and service checks
2. **Stage 1 (Analysis)**: LLM analyzes the service type and operational patterns
3. **Stage 2 (Generation)**: LLM generates a self-contained Python simulator
4. **Execution**: Runs the script, auto-fixes errors if needed (up to 3 retries)

## Options

| Option | Description |
|--------|-------------|
| `--scenario`, `-s` | Scenario to simulate (healthy, degraded, incident, etc.) |
| `--duration, -d` | Duration in seconds (0 = run forever, default) |
| `--rate, -r` | Target metrics per batch (default: 100) |
| `--save` | Save script to integration's fake_data/ directory |
| `--show-only` | Display generated script without executing |
| `--timeout` | Execution timeout in seconds (for testing) |
| `--all-metrics` | Generate ALL metrics, not just dashboard metrics |
| `--sandbox/--no-sandbox` | Run in Docker container for isolation (default: enabled) |

**Note**: Sandbox mode is enabled by default and requires Docker Desktop to be running. Start Docker with `open -a Docker` on macOS. Use `--no-sandbox` to run directly on host.
