# Apache NiFi Agent Integration — PoC

Proof-of-concept demonstrating that the NiFi REST API provides all metrics
needed for a Datadog Agent integration. Runs NiFi 2.8.0 in Docker and queries
every monitoring endpoint the integration will use.

**RFC**: [AI-6667](https://datadoghq.atlassian.net/browse/AI-6667)
**Epic**: [AI-6662](https://datadoghq.atlassian.net/browse/AI-6662)

## Quick Start

```bash
cd nifi/poc
./scripts/run-poc.sh
```

This will:
1. Start NiFi 2.8.0 in Docker (HTTPS, single-user auth)
2. Wait for the API to become available (~60-90s)
3. Create test flows via REST API:
   - **Happy path**: GenerateFlowFile → LogMessage (produces throughput metrics)
   - **Error path**: GenerateFlowFile → PutFile /nonexistent (produces ERROR bulletins)
4. Wait for data to flow (30s)
5. Query all monitoring endpoints and save responses to `responses/`

## Endpoints Tested

| Endpoint | Purpose | Integration Use |
|----------|---------|-----------------|
| `GET /flow/about` | Version detection | Cached tag, connectivity check |
| `GET /system-diagnostics` | JVM heap, GC, threads, repos | System health metrics |
| `GET /flow/status` | Running/stopped/invalid counts | Flow summary metrics |
| `GET /flow/process-groups/root/status?recursive=true` | All component data in one call | Process group, processor, connection metrics |
| `GET /flow/cluster/summary` | Cluster vs standalone detection | Cluster health metrics |
| `GET /flow/bulletin-board` | Errors and warnings | Datadog events |

## Authentication

NiFi 2.x requires HTTPS and authentication. This PoC uses single-user mode:

```
Username: admin
Password: ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB
```

Token obtained via `POST /access/token` (returns JWT, 12h expiry).

## Teardown

```bash
cd nifi/poc
docker compose down -v
```

## NiFi UI

While running: https://localhost:8443/nifi/ (accept self-signed cert)
