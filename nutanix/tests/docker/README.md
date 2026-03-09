# Docker-based Integration Tests for Nutanix

This directory contains the Docker Compose setup for running integration tests against a mock Nutanix Prism Central API server.

## Architecture

- **Python Flask Server**: Lightweight HTTP server that serves API fixtures with pagination logic
- **Fixtures**: Reuses existing test fixtures from `../fixtures/` directory
- **Docker Compose**: Orchestrates the Python container

## Directory Structure

```
docker/
├── docker-compose.yaml       # Docker Compose configuration
├── mock_server.py            # Flask server that serves fixtures
└── README.md                 # This file

../fixtures/                  # Shared test fixtures (used by both mocked and Docker tests)
├── clusters.json
├── vms.json
├── events.json
├── alerts.json
├── tasks.json
└── ...
```

## How It Works

The Flask server (`mock_server.py`):
- Reads fixtures from `../fixtures/` directory
- Handles pagination via `$page` query parameter
- Applies time-based filtering for events/audits/alerts/tasks
- Mimics Nutanix Prism Central v4 API responses

**Key Features:**
- ✅ No fixture duplication - uses same files as unit tests
- ✅ Supports array-based fixture format (pages as JSON array)
- ✅ Handles `$filter` query parameters for time filtering
- ✅ Pagination logic matches the mocked test behavior

## Setup

No setup required! The fixtures are already in `../fixtures/` and are shared with unit tests.

## Running Integration Tests

### Using Docker (default)

```bash
# Run all tests (including integration tests)
ddev test nutanix

# Run only integration tests
ddev test nutanix -- -k test_integration
```

The `dd_environment` pytest fixture automatically:
- Starts the Docker Compose services
- Waits for the Flask server to be healthy
- Runs tests against the mock API
- Cleans up containers after tests

### Using Real Nutanix Environment

To test against a real Nutanix Prism Central instance:

1. Add an entry to your `/etc/hosts` file:
   ```bash
   # For local Nutanix instance
   192.168.1.100  nutanix.local

   # Or for remote/cloud instance
   <PRISM_CENTRAL_IP>  nutanix.local
   ```

2. Set the environment variable and run tests:
   ```bash
   export USE_NUTANIX_AWS=true
   ddev test nutanix -- -k test_integration
   ```

The tests will connect to `https://nutanix.local:9440` which resolves to the IP you configured in `/etc/hosts`.

## API Endpoints

The Flask server mocks the following Nutanix Prism Central v4 APIs:

### Infrastructure APIs
- `GET /api/clustermgmt/v4.0/config/clusters` - List clusters (paginated)
- `GET /api/clustermgmt/v4.0/config/clusters/{id}/hosts` - List hosts (paginated)
- `GET /api/clustermgmt/v4.0/stats/clusters/{id}` - Cluster stats
- `GET /api/clustermgmt/v4.0/stats/clusters/{id}/hosts/{id}` - Host stats

### VM APIs
- `GET /api/vmm/v4.0/ahv/config/vms` - List VMs (paginated)
- `GET /api/vmm/v4.0/ahv/stats/vms` - VM stats (paginated)

### Activity APIs
- `GET /api/monitoring/v4.0/serviceability/events` - List events (paginated, time-filtered)
- `GET /api/monitoring/v4.0/serviceability/audits` - List audits (paginated, time-filtered)
- `GET /api/monitoring/v4.0/serviceability/alerts` - List alerts (paginated, time-filtered)
- `GET /api/monitoring/v4.2/serviceability/alerts` - List alerts v4.2 (paginated, time-filtered)
- `GET /api/prism/v4.0/config/tasks` - List tasks (paginated, time-filtered)

### Metadata APIs
- `GET /api/prism/v4.0/config/categories` - List categories (paginated)

### Health Check
- `GET /console` - Health check endpoint

## Pagination

Paginated endpoints support the `$page` query parameter:
- `GET /api/.../endpoint?$page=0` - Returns page 0
- `GET /api/.../endpoint?$page=1` - Returns page 1
- Default: page 0 if not specified

Fixtures store pages as JSON arrays, e.g., `events.json`:
```json
[
  {"data": [...], "metadata": {...}},  // Page 0
  {"data": [...], "metadata": {...}},  // Page 1
  ...
]
```

## Time Filtering

Activity endpoints support time-based filtering via `$filter` parameter:
- Events: `?$filter=creationTime gt 2026-01-02T14:35:00Z`
- Audits: `?$filter=creationTime gt 2026-01-02T14:35:00Z`
- Alerts: `?$filter=creationTime gt 2026-01-02T14:35:00Z`
- Tasks: `?$filter=createdTime gt 2026-01-02T14:35:00Z`

The server filters and sorts results based on the timestamp.

## Manual Testing

You can manually test the Docker setup:

```bash
# Start services
cd nutanix/tests/docker
docker-compose up -d

# Wait for container to be ready
docker logs -f nutanix-prism-central
# Wait until you see "Starting Nutanix mock API server"

# Test health check
curl http://localhost:9440/console

# Test clusters endpoint (page 0)
curl http://localhost:9440/api/clustermgmt/v4.0/config/clusters

# Test with pagination
curl "http://localhost:9440/api/monitoring/v4.0/serviceability/events?\$page=1"

# Test with time filter
curl "http://localhost:9440/api/monitoring/v4.0/serviceability/events?\$filter=creationTime%20gt%202026-01-02T14:35:00Z"

# Stop services
docker-compose down
```

## Updating Fixtures

When you need to update the fixtures:

1. Update the fixtures in `../fixtures/` directory
2. Restart Docker services if they're running:
   ```bash
   docker-compose restart
   ```

That's it! The same fixtures are used by both unit tests and Docker integration tests.

## Troubleshooting

### Flask server not starting
```bash
# Check logs
docker logs nutanix-prism-central

# Common issues:
# - Flask installation failed (check pip output)
# - Fixtures directory not mounted (check volume mounts)
```

### Fixtures not found
Ensure fixtures exist in `../fixtures/` directory. You can verify:
```bash
ls -la ../fixtures/
```

### Port conflicts
If port 9440 is already in use, modify `docker-compose.yaml` to use a different port mapping:
```yaml
ports:
  - "9441:9440"  # Host:Container
```

Then update test configuration to use the new port.

### Container keeps restarting
Check if Flask is installed correctly:
```bash
docker logs nutanix-prism-central | grep -i error
```

## Comparison with vsphere Integration

Unlike vsphere (which uses pure Python mocking), this setup:
- Provides more realistic E2E testing with actual HTTP calls
- Tests serialization/deserialization over the wire
- Validates HTTP client behavior (retries, timeouts, etc.)
- Closer to production behavior

Both approaches have value:
- **Unit tests** (Python mocking): Fast, isolated, good for logic testing
- **Docker tests** (this setup): Slower, realistic, good for integration testing
