# n8n Test Environment

This directory contains Docker configuration for running an n8n instance with metrics and logging enabled for integration testing.

## Prerequisites

- Docker
- Docker Compose

## Usage

### Starting the environment

```bash
cd tests/docker
docker-compose up -d
```

### Accessing n8n

- **Web UI**: http://localhost:5678
- **Metrics endpoint**: http://localhost:5678/metrics
- **Health check**: http://localhost:5678/healthz

Default credentials:
- Username: `admin`
- Password: `admin`

### Viewing logs

```bash
docker-compose logs -f n8n
```

### Stopping the environment

```bash
docker-compose down
```

### Cleaning up (including volumes)

```bash
docker-compose down -v
```

## Configuration

### Metrics

The following metrics are enabled:
- Default system metrics
- Cache metrics
- Message event bus metrics
- API endpoint metrics
- Workflow ID labels on workflow metrics

The metrics are exposed in Prometheus/OpenMetrics format at `http://localhost:5678/metrics`.

### Logging

Logs are configured with:
- Log level: `debug`
- Log output: `console`
- Log directory: `./logs` (can be overridden with `N8N_LOG_FOLDER` environment variable)

### Environment Variables

You can override environment variables by setting them before running docker-compose:

```bash
N8N_LOG_FOLDER=/path/to/logs docker-compose up -d
```

## Testing

This setup is designed for integration testing. The n8n instance will:
1. Start with metrics endpoint enabled
2. Expose detailed logs for debugging
3. Include workflow_id labels in workflow metrics
4. Provide a health check endpoint for monitoring readiness

## Notes

- The container uses the latest official n8n Docker image
- Data is persisted in a Docker volume named `n8n_data`
- The health check waits up to 30 seconds for n8n to start before marking it as healthy

