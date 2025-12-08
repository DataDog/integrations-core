# Local Development with MinIO

This guide explains how to use the `--local` flag with `ddev release` commands for local development and testing without requiring AWS S3 access.

## Overview

The `--local` flag allows you to test the entire wheel upload and TUF signing workflow locally using MinIO, an S3-compatible object storage server running in Docker. MinIO is **automatically started** when you use the `--local` flag for the first time.

## Prerequisites

- Docker installed and running
- `ddev` command-line tool installed

## Quick Start

### 1. Build an Integration

```bash
ddev release build postgres
```

This creates the wheel and pointer file in the integration's `dist/` directory. The `--local` flag has no effect on the build command.

### 2. Upload to Local MinIO

```bash
ddev release upload --local --public postgres
```

This will:

- **Automatically start MinIO** if not already running (Docker container `ddev-minio-local`)
- Upload the wheel to `simple/datadog-postgres/`
- Upload the pointer file to `pointers/datadog-postgres/`
- Generate PEP 503 simple indexes at `simple/index.html` and `simple/datadog-postgres/index.html`
- Skip AWS authentication (uses hardcoded MinIO credentials)

**MinIO Console:** http://localhost:9001 (login: `minioadmin`/`minioadmin`)

### 3. Sign TUF Metadata

```bash
ddev release sign --local --generate-keys
```

This will:

- **Ensure MinIO is running** (starts automatically if needed)
- Generate dummy Ed25519 keys (if `--generate-keys` is specified)
- List all pointer files in MinIO
- Generate TUF metadata (root.json, targets.json, snapshot.json, timestamp.json)
- Sign metadata with the keys
- Upload signed metadata to `metadata/` prefix
- Save metadata files locally to `/tmp/tuf_metadata/`

### 4. Verify Upload

Check the MinIO console at http://localhost:9001 (login with `minioadmin`/`minioadmin`), or use the AWS CLI:

```bash
# Set MinIO credentials for AWS CLI
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin

# List wheels
aws --endpoint-url http://localhost:9000 s3 ls s3://test-public-integration-wheels/simple/datadog-postgres/

# List pointers
aws --endpoint-url http://localhost:9000 s3 ls s3://test-public-integration-wheels/pointers/datadog-postgres/

# List TUF metadata
aws --endpoint-url http://localhost:9000 s3 ls s3://test-public-integration-wheels/metadata/
```

### 5. Test the Downloader

To test downloading wheels using the local TUF-enabled downloader:

```bash
# IMPORTANT: Fetch root.json from MinIO (not /tmp/tuf_metadata/)
# This ensures you have the exact root.json that matches the signed metadata
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
aws --endpoint-url http://localhost:9000 s3 cp \
  s3://test-public-integration-wheels/metadata/root.json \
  datadog_checks_downloader/datadog_checks/downloader/data/repo/metadata/root.json

# Set up the downloader venv (if not already done)
cd datadog_checks_downloader
python -m venv .venv
source .venv/bin/activate
pip install -e '.[deps]'

# Download from local MinIO (no credentials needed - bucket is public for local testing)
python -m datadog_checks.downloader datadog-postgres \
  --repository http://localhost:9000/test-public-integration-wheels
```

**Important:**
- **Always fetch root.json from MinIO** after signing, not from `/tmp/tuf_metadata/`
- If you run `ddev release sign --local --generate-keys` multiple times, NEW keys are generated each time
- The downloader must use the exact root.json that matches the keys used to sign the metadata in MinIO
- The committed root.json contains production keys; the local root.json contains dummy keys
- Local MinIO bucket is configured for anonymous downloads (no AWS credentials needed)
- **Metadata cache is automatically cleared** when using localhost URLs - no manual deletion required after running `ddev release sign --local`

## Managing MinIO

MinIO is automatically managed by the `ddev release` commands when using `--local`. However, you can also manage it manually using Docker:

### Check if MinIO is Running

```bash
docker ps | grep ddev-minio-local
```

### View MinIO Logs

```bash
docker logs ddev-minio-local
```

### Stop MinIO

```bash
docker stop ddev-minio-local
```

### Start MinIO (if stopped)

```bash
docker start ddev-minio-local
```

### Remove MinIO Container and Data

```bash
docker rm -f ddev-minio-local
```

**Note:**

- MinIO will automatically restart when you run `ddev release upload --local` or `ddev release sign --local`
- Data is stored inside the container (ephemeral) - removing the container deletes all uploaded wheels and metadata
- To clean up after testing, simply remove the container: `docker rm -f ddev-minio-local`

## Complete Workflow Example

```bash
# 1. Build, upload, and sign multiple integrations
# MinIO starts automatically on first --local command
for integration in postgres mysql redis; do
  ddev release build "$integration"
  ddev release upload --local --public "$integration"
done

# 2. Sign all uploaded integrations
ddev release sign --local --generate-keys

# 3. Fetch root.json from MinIO to downloader
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
aws --endpoint-url http://localhost:9000 s3 cp \
  s3://test-public-integration-wheels/metadata/root.json \
  datadog_checks_downloader/datadog_checks/downloader/data/repo/metadata/root.json

# 4. Test downloading (no credentials needed for local MinIO)
cd datadog_checks_downloader
python -m datadog_checks.downloader datadog-postgres \
  --repository http://localhost:9000/test-public-integration-wheels
```

## Data Lifecycle

**Ephemeral Storage:**

- All data is stored inside the MinIO container without persistent volumes
- Data persists while the container exists (running or stopped)
- Data is **deleted** when you remove the container

**Typical workflow:**

1. Container created automatically on first `--local` command
2. Upload wheels/pointers, generate metadata across multiple test runs
3. When done testing: `docker rm -f ddev-minio-local` cleans everything up
4. Next `--local` command starts fresh with an empty bucket

This is ideal for testing - you get a clean slate each time you restart testing.

## Differences from Production

### Local Mode

- Uses MinIO on `http://localhost:9000`
- Bucket configured for **anonymous downloads** (no authentication needed for reads)
- Admin credentials (`minioadmin`/`minioadmin`) only needed for AWS CLI/management operations
- Data stored in Docker container (ephemeral - deleted on container removal)

### Production Mode

- Uses AWS S3 in `eu-north-1` region
- Requires AWS credentials via aws-vault or environment variables
- Bucket: `test-public-integration-wheels`
- Data persisted permanently in S3

## Troubleshooting

### Docker Not Available

If you see "Docker is not available", ensure Docker Desktop is installed and running:

```bash
# Check Docker status
docker ps
```

### MinIO Won't Start

If MinIO fails to start automatically:

```bash
# Check if ports are already in use
lsof -i :9000
lsof -i :9001

# Remove existing container and try again
docker rm -f ddev-minio-local

# Retry the command
ddev release upload --local --public postgres
```

### Upload Fails with Connection Error

```bash
# Check if MinIO is running
docker ps | grep ddev-minio-local

# View MinIO logs
docker logs ddev-minio-local

# Restart MinIO
docker restart ddev-minio-local
```

### TUF Metadata Generation Fails

```bash
# Ensure pointers were uploaded first
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
aws --endpoint-url http://localhost:9000 s3 ls \
  s3://test-public-integration-wheels/pointers/

# Check local metadata directory
ls -la /tmp/tuf_metadata/
```

### Downloader Shows "timestamp was signed by 0/1 keys"

This means the downloader's root.json doesn't match the keys used to sign the metadata in MinIO.

**Root Cause:**
- Running `ddev release sign --local --generate-keys` generates NEW keys each time
- If you run it multiple times, the latest metadata in MinIO is signed with the newest keys
- But your downloader may have a root.json from an earlier run with different keys

**Solution - Fetch root.json from MinIO:**

```bash
# ALWAYS fetch root.json from MinIO after signing (not /tmp/tuf_metadata/)
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
aws --endpoint-url http://localhost:9000 s3 cp \
  s3://test-public-integration-wheels/metadata/root.json \
  datadog_checks_downloader/datadog_checks/downloader/data/repo/metadata/root.json
```

**Alternative - Reuse existing keys:**

```bash
# Don't generate new keys - reuse keys from ~/.ddev/tuf_keys/
ddev release sign --local  # No --generate-keys flag
```

**Verify keyids match:**

```bash
# Check if keyids in root.json match the signed metadata
python3 << 'EOF'
import json
root = json.load(open('datadog_checks_downloader/datadog_checks/downloader/data/repo/metadata/root.json'))
timestamp = json.load(open('/tmp/timestamp_from_minio.json'))
expected = root['signed']['roles']['timestamp']['keyids'][0]
actual = timestamp['signatures'][0]['keyid']
print(f"✅ Match!" if expected == actual else f"❌ Mismatch!\nExpected: {expected}\nActual: {actual}")
EOF
```

## File Locations

### Local

- **MinIO Data**: Stored in Docker container volume
- **TUF Keys**: `~/.ddev/tuf_keys/` (default)
- **TUF Metadata**: `/tmp/tuf_metadata/` (default)
- **Build Artifacts**: `{integration}/dist/`

### MinIO Bucket Structure

```
test-public-integration-wheels/
├── simple/
│   ├── index.html                    # Root package index
│   └── datadog-{integration}/
│       ├── index.html                # Package-specific index
│       └── datadog_{integration}-{version}-py3-none-any.whl
├── pointers/
│   └── datadog-{integration}/
│       └── datadog_{integration}-{version}.pointer
└── metadata/                         # TUF metadata
    ├── root.json
    ├── targets.json
    ├── snapshot.json
    └── timestamp.json
```

## Notes

- The `--local` flag only affects `upload` and `sign` commands
- The `build` command works the same in local and production modes
- TUF keys generated with `--generate-keys` are dummy keys for POC/testing only
- MinIO data is ephemeral - removing the container deletes all data
- For production use, always use the production S3 bucket with proper key management
