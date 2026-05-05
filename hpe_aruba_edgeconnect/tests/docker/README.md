# Fake HPE Aruba EdgeConnect Orchestrator

Docker-based fake orchestrator for E2E testing of the `hpe_aruba_edgeconnect` integration.

## Architecture

A lightweight Flask app serves a minimal subset of the EdgeConnect Orchestrator REST API over **HTTPS** (self-signed certificate generated at image build time). The container exposes port **8443** and the host port is chosen dynamically — `conftest.py` automatically picks a free port and exports `HOST_PORT` if it is not already set.

## Directory structure

```
tests/
├── docker/
│   ├── docker-compose.yaml
│   ├── README.md
│   └── fake_orch/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app.py
└── fixtures/
    └── st2-123456789.tgz   # must exist before building the image
```

## Endpoints

| Method | Path | Response |
|--------|------|----------|
| GET | `/gms/rest/appliance` | 200 — JSON array with one appliance object |
| GET | `/rest/json/stats/minuteRange` | 200 — `{"newest": 123456789}` |
| GET | `/rest/json/stats/minuteStats/st2-123456789.tgz` | 200 — streams the `.tgz` archive (`application/gzip`) |
| GET | `/rest/json/stats/minuteStats/<other>` | 404 — JSON error |
| GET | `/health` | 200 — `{"status": "ok"}` |

## Running with ddev

### 1. List available environments

`HOST_PORT` is auto-assigned by `conftest.py` when not set. You can override it manually if needed:

```bash
export HOST_PORT=18443  # optional
```

```bash
ddev env show hpe_aruba_edgeconnect
```

### 2. Start the environment

```bash
ddev env start --dev hpe_aruba_edgeconnect <ENV>
```

### 3. Run the E2E tests

```bash
ddev env test --dev hpe_aruba_edgeconnect <ENV>
```

### 5. Stop the environment

```bash
ddev env stop hpe_aruba_edgeconnect <ENV>
```

## Manual docker-compose usage

```bash
cd hpe_aruba_edgeconnect/tests/docker
export HOST_PORT=18443
docker compose up --build -d
curl -k https://localhost:18443/health
docker compose down
```

## Fixture requirement

`tests/fixtures/st2-123456789.tgz` **must** exist before `docker compose build`. The `COPY` instruction in the Dockerfile will fail at build time if the archive is missing.
