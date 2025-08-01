# Krakend Integration Traffic Generator

This tool is used to start the Krakend test environment and generate traffic to the Krakend endpoints. This is useful for testing the Datadog integration for Krakend and generating metrics.

## Setup

### Configuration

#### Datadog Credentials

The lab uses the `.ddev` configuration file to override `ddev` configuration. This file should be located anywhere within the `krakend` folder. If you already have a `.ddev` file, locate this file directly in the `lab` folder to only affect the execution of the lab.

```
org = "krakendlab"

[orgs.krakendlab]
api_key = "your-actual-api-key"
site = "datadoghq.com"
```

**Important**: Replace `"your-actual-api-key"` with your actual Datadog API key. The site should be set to your Datadog site (e.g., `datadoghq.com`, `datadoghq.eu`, etc.).

#### Traffic Configuration

The traffic generator uses a `config.yaml` file located in the `tests/lab/` directory to control request probabilities. This file can be modified while the traffic generator is running, and changes will be automatically picked up every 5 seconds.

```yaml
# Krakend Traffic Generator Configuration
request_probabilities:
  /api/valid: 0.75              # Successful requests
  /api/invalid: 0.05            # Invalid requests
  /api/timeout: 0.05            # Timeout scenarios
  /api/no-content-length: 0.05  # Edge case scenarios
  /api/not-found: 0.05          # 404 errors
  /api/cancelled: 0.05          # Cancelled requests

# Configuration reload interval in seconds
reload_interval: 5
```

**Dynamic Configuration**: You can modify the probabilities in `config.yaml` while the traffic generator is running to change the traffic patterns in real-time. For example, increase `/api/timeout` to 0.5 to generate more timeout scenarios, or set `/api/valid` to 0.9 for mostly successful requests.

**Validation**: The configuration is automatically validated when loaded. All probabilities must:
- Be numeric values between 0 and 1
- Sum to exactly 1.0 (with a small tolerance for floating-point precision)

If the configuration is invalid, the traffic generator will display a warning message and continue using the previous valid configuration. Example validation errors:
- `Probabilities must sum to 1.0, current sum is 0.85`
- `Probability for '/api/timeout' must be between 0 and 1, got 1.5`

## Usage

The traffic lab is run using a bash script that ensures proper cleanup even when interrupted with Ctrl+C.

### Basic Usage

```bash
./tests/lab/run_traffic_lab.sh
```

### With Custom Environment

```bash
./tests/lab/run_traffic_lab.sh -e py3.12-2.10
```

### Available Options

```bash
./tests/lab/run_traffic_lab.sh --help
```

- `-e, --env ENV`: Environment to use (default: `py3.12-2.10`)
- `-h, --help`: Show help message

## What It Does

This command will:

1. **Environment Setup**: Start the Docker containers for the backend API, Krakend, and the Datadog Agent using `ddev`
2. **Health Check**: Verify that KrakenD is running and accessible at `http://localhost:8080/__health`
3. **Traffic Generation**: Begin sending requests to various Krakend endpoints with realistic traffic patterns. Each endpoint is called with different probabilities to simulate real-world usage:
   - `/api/valid` - Successful requests
   - `/api/invalid` - Invalid requests
   - `/api/timeout` - Timeout scenarios
   - `/api/no-content-length` - Edge case scenarios
   - `/api/not-found` - 404 errors
   - `/api/cancelled` - Cancelled requests
4. **Dynamic Configuration**: Automatically reload traffic configuration from `config.yaml` every 5 seconds, allowing you to modify request probabilities while the lab is running
5. **Real-time Display**: Show request results in a formatted table with timestamps, endpoints, status codes, and response times
6. **Graceful Cleanup**: Automatically tear down the test environment when stopped (Ctrl+C) or on script exit

## Stopping the Lab

To stop the traffic generation and clean up the environment, simply press `Ctrl+C`. The bash script uses a trap mechanism to ensure that the test environment is always properly cleaned up, even if the script is interrupted.

## Individual Commands

The traffic generator also supports running individual commands using hatch:

```bash
# Start environment only
hatch run lab:start

# Generate traffic only (assumes environment is already running)
hatch run lab:generate

# Stop environment only
hatch run lab:stop
```

However, it's recommended to use the bash script for the complete workflow as it handles cleanup automatically.
