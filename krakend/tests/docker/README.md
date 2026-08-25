# KrakenD Test Environment

This setup provides a complete [KrakenD][1] testing environment with a FastAPI backend.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client        │───▶│   KrakenD       │───▶│   FastAPI       │
│   (You)         │    │   Gateway       │    │   Backend       │
│   Port: N/A     │    │   Port: 8080    │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ OpenTelemetry   │
                       │ Metrics Endpoint│
                       │   Port: 9090    │
                       └─────────────────┘
```

## Services

### 1. KrakenD Gateway (Port 8080)
- **Purpose**: API Gateway that proxies requests to the FastAPI backend
- **Features**:
  - OpenTelemetry metrics export on port 9090
  - Request routing and transformation
  - Timeout handling (1 seconds)
  - Health checks at `/__health`

### 2. FastAPI Backend (Port 8000)
- **Purpose**: Provides test endpoints with different behaviors
- **Features**:
  - Content-Length headers on all responses
  - Custom exception handling
  - Async/await support

## API Endpoints (via KrakenD)

All endpoints are prefixed with `/api/` when accessed through KrakenD:

### 1. `/api/valid` (GET)
- **Purpose**: Returns a valid response with a dummy message
- **Response**: 200 OK with JSON payload
- **Example**: `{"message": "This is a valid response", "status": "success"}`

### 2. `/api/invalid` (GET)
- **Purpose**: Always fails when called
- **Response**: 500 Internal Server Error
- **Example**: `{"detail": "This endpoint always fails", "status_code": 500}`

### 3. `/api/timeout` (GET)
- **Purpose**: Takes more than 1 seconds to respond, causing timeout
- **Response**: 504 Gateway Timeout (from KrakenD after 1s timeout)
- **Backend**: Would return 200 OK after 3 seconds if not timed out

### 4. `/api/cancelled` (GET)
- **Purpose**: Simulates a cancelled request
- **Response**: 499 Client Closed Request
- **Example**: `{"detail": "Request cancelled", "status_code": 499}`

### 5. `/api/no-content-length` (GET)
- **Purpose**: Returns a response without a Content-Length header
- **Response**: 200 OK with a streamed JSON payload

## Running the Complete Stack

### Start All Services
```bash
cd tests/docker
docker-compose up --build -d
```

### Services will be available at:
- **KrakenD Gateway**: http://localhost:8080
- **KrakenD Metrics**: http://localhost:9090/metrics
- **FastAPI Backend**: http://localhost:8000 (direct access)

## Testing the Endpoints

Use the e2e tests to validate the complete setup:

```bash
# Start the test environment in detached mode
cd tests/docker

# Launch tests through ddev
ddev env test --base krakend py3.12-2.10
```

This command automates the entire testing process:
- 🐳 Spins up the required Docker containers.
- 🔄 Generates traffic for all API endpoints.
- 📊 Validates that all expected metrics are emitted.
- 🛑 Tears down the testing environment.


## Configuration Files

- **`krakend.json`**: KrakenD configuration with OpenTelemetry setup
- **`docker-compose.yml`**: The docker-compose file that spins up both the backend API and the KrakenD Gateway.
- **`api.py`**: FastAPI backend implementation
- **`Dockerfile`**: Dockerfile for the FastAPI backend.


[1]: https://www.krakend.io/