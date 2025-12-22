# Local Development Guide

## Overview

This guide covers local development and testing of the release pipeline. All releases are processed through GitHub Actions with TUF and SLSA 2 attestations.

**Note:** Local MinIO development has been removed. All releases now use AWS S3 via GitHub Actions CI.

## Prerequisites

- Python 3.11+
- `ddev` command-line tool installed
- AWS credentials configured (for testing S3 uploads)
- Access to GitHub Actions (for triggering release workflows)

## Local Development Workflow

### 1. Install Dependencies

```bash
cd datadog_checks_dev
pip install -e '.[deps]'
```

### 2. Build Integration Locally

Build wheels locally to test the build process and verify artifacts:

```bash
ddev release build postgres
```

This creates in the `postgres/dist/` directory:
- `datadog_postgres-{version}-py3-none-any.whl` - The wheel file
- `datadog-postgres-{version}.pointer` - Pointer file with wheel metadata
- `datadog-postgres-{version}-attestation.json` - SLSA 2 provenance attestation

### 3. Inspect Build Artifacts

**View Pointer File:**
```bash
cat postgres/dist/datadog-postgres-*.pointer
```

Example output:
```yaml
pointer:
  name: datadog-postgres
  version: 23.2.0
  uri: https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com/simple/datadog-postgres/datadog_postgres-23.2.0-py3-none-any.whl
  digest: 094609f2d2f7583325e0d2493fcabc3715afeaa1a3414ea964d883e2f765fc56
  length: 100905
  attestation:
    uri: https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com/attestations/datadog-postgres/datadog-postgres-23.2.0-attestation.json
    digest: 7f8a9b2c...
    length: 5432
```

**View SLSA 2 Attestation:**
```bash
cat postgres/dist/datadog-postgres-*-attestation.json | jq
```

Example output:
```json
{
  "_type": "https://in-toto.io/Statement/v0.1",
  "predicateType": "https://slsa.dev/provenance/v0.2",
  "subject": [
    {
      "name": "datadog_postgres-23.2.0-py3-none-any.whl",
      "digest": {
        "sha256": "094609f2..."
      }
    }
  ],
  "predicate": {
    "builder": {
      "id": "https://github.com/DataDog/integrations-core/.github/workflows/release.yml@main"
    },
    "buildType": "https://github.com/DataDog/integrations-core/build/wheel/v1",
    "metadata": {
      "buildInvocationId": "123456789",
      "buildStartedOn": "2025-12-08T18:00:00Z"
    }
  }
}
```

### 4. Run Tests Locally

```bash
# Run unit tests
ddev test postgres

# Run specific tests
ddev test postgres -- -k test_function_name

# Format code
ddev test -fs postgres
```

## GitHub Actions Testing

### Trigger Release Workflow

The release pipeline runs on GitHub Actions and can be triggered manually:

1. **Navigate to Actions tab** in the GitHub repository
2. Select **"Release Integration Package"** workflow
3. Click **"Run workflow"**
4. Configure inputs:
   - **Integration**: `postgres` (or any integration name)
   - **Dry run**: Check for testing without S3 upload
5. Click **"Run workflow"** to start

### Workflow Steps

The pipeline performs these steps automatically:

1. ✅ **Build wheel** - Creates wheel with SLSA 2 attestation
2. ✅ **Generate attestation** - SLSA 2 provenance in in-toto format
3. ✅ **Sign pointer** - TUF signature (mocked in POC)
4. ✅ **Sign attestation** - Sigstore signature (mocked in POC)
5. ✅ **Upload to S3** - Wheels, pointers, attestations
6. ✅ **Update TUF metadata** - Generate and upload signed metadata
7. ✅ **Update PyPI index** - Generate PEP 503 simple index
8. ✅ **Test downloader** - Verify end-to-end download with attestation

### Monitor Workflow Execution

View logs and artifacts in the GitHub Actions UI:

- **Build logs** - See each step's output
- **Artifacts** - Download built wheels and attestations
- **Summary** - View S3 locations and verification status

## Testing the Downloader

### With Production S3 Repository

After a successful GitHub Actions release, test the downloader:

```bash
cd datadog_checks_downloader

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install downloader
pip install -e .

# Download package with attestation verification
python -m datadog_checks.downloader datadog-postgres \
  --repository https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com
```

### Expected Output

```
INFO: Downloading attestation from: https://s3.../attestations/...
INFO: ✅ Attestation hash verified
INFO: ✅ [MOCK] Sigstore signature verified
INFO: ✅ [MOCK] SLSA provenance verified
INFO: ✅ Attestation verification passed
/path/to/datadog_postgres-23.2.0-py3-none-any.whl
```

### What Gets Verified

1. **TUF Metadata** - Cryptographic verification of pointer files
2. **Wheel Hash** - SHA256 verification from pointer
3. **Attestation Hash** - SHA256 verification of attestation file
4. **Attestation Structure** - Validates in-toto format
5. **Subject Matching** - Verifies wheel is in attestation subjects
6. **Sigstore Signature** - Mocked verification (POC only)

## S3 Bucket Structure

After upload, the S3 bucket contains:

```
test-public-integration-wheels/
├── simple/                          # PyPI simple index
│   ├── index.html
│   └── datadog-postgres/
│       ├── index.html
│       └── datadog_postgres-23.2.0-py3-none-any.whl
├── pointers/                        # TUF target files
│   └── datadog-postgres/
│       └── datadog-postgres-23.2.0.pointer
├── attestations/                    # SLSA provenance
│   └── datadog-postgres/
│       └── datadog-postgres-23.2.0-attestation.json
└── metadata/                        # TUF metadata
    ├── root.json
    ├── targets.json
    ├── snapshot.json
    └── timestamp.json
```

## CI Pipeline Configuration

### GitHub Secrets Required

Configure these secrets in your GitHub repository:

- **`AWS_RELEASE_ROLE_ARN`** - IAM role ARN for S3 uploads
  - Example: `arn:aws:iam::123456789:role/github-actions-release`
  - Permissions needed: `s3:PutObject`, `s3:GetObject`, `s3:ListBucket`

### Future: TUF Signing Keys

For production (not in POC):
- **`TUF_ROOT_KEY`** - Ed25519 private key (base64 encoded)
- **`TUF_TARGETS_KEY`** - Ed25519 private key (base64 encoded)
- **`TUF_SNAPSHOT_KEY`** - Ed25519 private key (base64 encoded)
- **`TUF_TIMESTAMP_KEY`** - Ed25519 private key (base64 encoded)

### Workflow Triggers

The workflow can be triggered:

1. **Manually** - From GitHub Actions UI (workflow_dispatch)
2. **On PR merge** - Automatically when PR is merged (future)
3. **On tag push** - Automatically on version tags (future)

## Development Without S3

For pure local testing without S3 access:

```bash
# Build only
ddev release build postgres

# Run unit tests
ddev test postgres

# Format code
ddev test -fs postgres

# Manual artifact verification
python -c "
import yaml
import json

# Check pointer format
with open('postgres/dist/datadog-postgres-23.2.0.pointer') as f:
    pointer = yaml.safe_load(f)
    print('Pointer:', json.dumps(pointer, indent=2))

# Check attestation format
with open('postgres/dist/datadog-postgres-23.2.0-attestation.json') as f:
    attestation = json.load(f)
    print('Attestation type:', attestation['_type'])
    print('Predicate type:', attestation['predicateType'])
"
```

**Note:** Full integration testing (TUF verification, attestation download) requires S3 access via GitHub Actions.

## Common Issues

### Issue: "Failed to connect to S3"

**Solution:** Ensure AWS credentials are configured:
```bash
# Configure AWS SSO
aws configure sso

# Or use aws-vault
aws-vault exec your-profile -- ddev release upload postgres
```

### Issue: "Attestation verification failed"

**Cause:** This is expected for local builds without real Sigstore signatures.

**Solution:** The POC mocks Sigstore verification. In production, attestations would be signed with real Sigstore/cosign.

### Issue: "TUF signature verification failed"

**Cause:** The downloader's root.json doesn't match production metadata.

**Solution:** Ensure you're using the correct root.json:
```bash
cd datadog_checks_downloader
curl -o datadog_checks/downloader/data/repo/metadata/root.json \
  https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com/metadata/root.json
```

### Issue: GitHub Actions workflow fails at upload step

**Cause:** AWS OIDC authentication not configured or IAM role lacks permissions.

**Solution:**
1. Verify `AWS_RELEASE_ROLE_ARN` secret is set
2. Check IAM role trust policy allows GitHub OIDC
3. Verify IAM role has S3 permissions

## File Locations

### Local Build Artifacts
- **Build output**: `{integration}/dist/`
- **Wheel**: `{integration}/dist/{package_name}-{version}-py3-none-any.whl`
- **Pointer**: `{integration}/dist/{package_name}-{version}.pointer`
- **Attestation**: `{integration}/dist/{package_name}-{version}-attestation.json`

### GitHub Actions Artifacts
- **Available in workflow run** under "Artifacts" tab
- **Retention**: 90 days (GitHub default)

### S3 Production Artifacts
- **Region**: `eu-north-1`
- **Bucket**: `test-public-integration-wheels`
- **Wheels**: `s3://.../simple/{package}/`
- **Pointers**: `s3://.../pointers/{package}/`
- **Attestations**: `s3://.../attestations/{package}/`
- **TUF Metadata**: `s3://.../metadata/`

## POC Limitations

⚠️ **This is a POC with mocked security features:**

- **TUF signing** uses dummy Ed25519 keys (not HSM)
- **Sigstore signatures** are mocked (no actual cosign)
- **Key rotation** not implemented
- **HSM/KMS integration** not implemented
- **Attestation verification** is simplified

**For production, implement:**
- HSM-backed TUF keys with proper key ceremony
- Real Sigstore/cosign integration
- Key rotation procedures
- Offline root keys with threshold signatures
- Multi-party signing for release approval
- Rekor transparency log verification
- Integration with organizational PKI

## Next Steps

1. **Test builds locally** - Verify wheel and attestation generation
2. **Trigger GitHub Actions** - Test full pipeline with dry-run
3. **Download and verify** - Test downloader with attestation verification
4. **Review artifacts** - Inspect S3 bucket structure and metadata
5. **Iterate** - Make changes and re-run pipeline

For questions or issues, consult the main README.md or GitHub Actions logs.
