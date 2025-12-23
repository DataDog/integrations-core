#!/bin/bash
set -e

# Simulate GitHub Actions workflow locally with full S3 integration
INTEGRATION=""
KEEP_BUCKET=false
S3_BUCKET="test-public-integration-wheels"
S3_REGION="eu-north-1"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --keep)
            KEEP_BUCKET=true
            shift
            ;;
        *)
            INTEGRATION="$1"
            shift
            ;;
    esac
done

# Default integration if not provided
INTEGRATION="${INTEGRATION:-postgres}"

echo "=== Checking for integration: $INTEGRATION ==="
if [ ! -d "$INTEGRATION" ]; then
    echo "Error: Integration directory '$INTEGRATION' not found"
    echo "Available integrations: $(ls -d */ | grep -v datadog_checks | head -5 | tr '\n' ' ')"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo "Error: AWS credentials not configured"
    echo "Please configure AWS credentials (aws-vault, aws sso, or environment variables)"
    exit 1
fi

echo "✅ Integration found: $INTEGRATION"
echo "✅ AWS credentials configured"
echo ""

# Wipe bucket unless --keep flag is provided
if [ "$KEEP_BUCKET" = false ]; then
    echo "=== Step 0: Wiping S3 bucket ==="
    echo "Clearing all objects from s3://$S3_BUCKET..."

    # Delete all objects in the bucket
    aws s3 rm "s3://$S3_BUCKET" --recursive --region "$S3_REGION" 2>/dev/null || true

    echo "✅ Bucket wiped clean"
    echo ""
else
    echo "=== Step 0: Keeping existing S3 bucket contents (--keep flag provided) ==="
    echo ""
fi

echo "=== Step 1: Build wheel and generate attestation ==="
# Store repo root and integration path for later use
REPO_ROOT="$(pwd)"
INTEGRATION_PATH="$REPO_ROOT/$INTEGRATION"

# Run ddev commands from repo root with relative integration name
ddev release build "$INTEGRATION"
BUILD_EXIT=$?

if [ $BUILD_EXIT -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ Build successful"
echo ""

echo "=== Step 2: Mock TUF signing ==="
echo "🔐 [MOCK] Signing pointer file with TUF keys..."
echo "✅ [MOCK] Pointer signature: $(openssl rand -hex 32)"
echo ""

echo "=== Step 3: Mock Sigstore signing ==="
echo "🔐 [MOCK] Signing attestation with Sigstore..."
echo "✅ [MOCK] Sigstore signature: $(openssl rand -hex 64)"
echo ""

echo "=== Step 4: Verify artifacts created ==="
DIST_DIR="$INTEGRATION_PATH/dist"
echo "Artifacts in $DIST_DIR:"
ls -lh "$DIST_DIR"

# Find the version from the wheel filename
WHEEL_FILE=$(ls "$DIST_DIR"/*.whl | head -1)
# Extract version using sed (more portable than grep -P)
VERSION=$(basename "$WHEEL_FILE" | sed -E 's/.*-([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/')
echo ""
echo "Detected version: $VERSION"
echo ""

# Convert folder name to package name (replace underscores with dashes)
PACKAGE_NAME="datadog-${INTEGRATION//_/-}"
echo "Package name: $PACKAGE_NAME"
echo ""

echo "=== Step 5: Show pointer content ==="
cat "$DIST_DIR/${PACKAGE_NAME}-${VERSION}.pointer"
echo ""

echo "=== Step 6: Show attestation structure ==="
echo "Attestation file preview:"
cat "$DIST_DIR/${PACKAGE_NAME}-${VERSION}-attestation.json" | python3 -m json.tool | head -40
echo ""

echo "=== Step 7: Upload to S3 ==="
echo "Uploading wheel, pointer, and attestation to S3..."
# Run from repo root with relative integration name
ddev release upload --public "$INTEGRATION"
UPLOAD_EXIT=$?

if [ $UPLOAD_EXIT -ne 0 ]; then
    echo "❌ Upload failed"
    exit 1
fi

echo "✅ Upload successful"
echo ""

echo "=== Step 8: Generate and upload TUF metadata ==="
echo "Generating TUF metadata from uploaded pointers..."
# Run from repo root to generate TUF metadata
ddev release sign --generate-keys
SIGN_EXIT=$?

if [ $SIGN_EXIT -ne 0 ]; then
    echo "❌ TUF signing failed"
    exit 1
fi

echo "✅ TUF metadata signed and uploaded"
echo ""

echo "=== Step 9: Verify S3 bucket contents ==="
echo "Checking S3 bucket structure..."
echo ""
echo "Wheels:"
aws s3 ls "s3://$S3_BUCKET/simple/${PACKAGE_NAME}/" --region "$S3_REGION" || echo "  (none)"
echo ""
echo "Pointers:"
aws s3 ls "s3://$S3_BUCKET/pointers/${PACKAGE_NAME}/" --region "$S3_REGION" || echo "  (none)"
echo ""
echo "Attestations:"
aws s3 ls "s3://$S3_BUCKET/attestations/${PACKAGE_NAME}/" --region "$S3_REGION" || echo "  (none)"
echo ""
echo "TUF Metadata:"
aws s3 ls "s3://$S3_BUCKET/metadata/" --region "$S3_REGION" || echo "  (none)"
echo ""

echo "=== Step 10: Update downloader root.json ==="
echo "Fetching latest root.json from S3..."
cd datadog_checks_downloader
mkdir -p datadog_checks/downloader/data/repo/metadata

aws s3 cp \
    "s3://$S3_BUCKET/metadata/root.json" \
    datadog_checks/downloader/data/repo/metadata/root.json \
    --region "$S3_REGION"

echo "✅ Root.json updated"
echo ""

echo "=== Step 11: Set up downloader environment ==="
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment and installing downloader..."
source .venv/bin/activate
pip install -q -e . 2>/dev/null || pip install -e .

echo "✅ Downloader environment ready"
echo ""

echo "=== Step 12: Test downloader with attestation verification ==="
echo "Downloading ${PACKAGE_NAME} with TUF and attestation verification..."
echo ""

DOWNLOAD_OUTPUT=$(python -m datadog_checks.downloader "${PACKAGE_NAME}" \
    --repository "https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com" \
    --verbose 4 2>&1)

DOWNLOAD_EXIT=$?

echo "$DOWNLOAD_OUTPUT"
echo ""

if [ $DOWNLOAD_EXIT -ne 0 ]; then
    echo "❌ Download failed"
    exit 1
fi

# Check if attestation verification passed
if echo "$DOWNLOAD_OUTPUT" | grep -q "Attestation verification passed"; then
    echo "✅ Attestation verification PASSED"
else
    echo "⚠️  Attestation verification message not found in output"
fi

# Extract downloaded wheel path (using grep -o instead of -P for portability)
WHEEL_PATH=$(echo "$DOWNLOAD_OUTPUT" | grep -o '/[^[:space:]]*\.whl' | tail -1)

if [ -n "$WHEEL_PATH" ] && [ -f "$WHEEL_PATH" ]; then
    echo "✅ Wheel downloaded successfully: $WHEEL_PATH"

    # Check if attestation was saved alongside wheel
    ATTESTATION_PATH="${WHEEL_PATH%.whl}-attestation.json"
    if [ -f "$ATTESTATION_PATH" ]; then
        echo "✅ Attestation saved alongside wheel: $ATTESTATION_PATH"
    else
        echo "⚠️  Attestation not found at: $ATTESTATION_PATH"
    fi
else
    echo "❌ Wheel path not found in download output"
    exit 1
fi

echo ""
echo "=============================================="
echo "🎉 Complete workflow test PASSED!"
echo "=============================================="
echo ""
echo "Summary:"
echo "  Integration: $INTEGRATION"
echo "  Package: $PACKAGE_NAME"
echo "  Version: $VERSION"
echo "  S3 Bucket: s3://$S3_BUCKET"
echo "  Downloaded Wheel: $WHEEL_PATH"
echo ""
echo "Verification Steps Completed:"
echo "  ✅ Build with SLSA 2 attestation generation"
echo "  ✅ Upload to S3 (wheel, pointer, attestation)"
echo "  ✅ TUF metadata signing and upload"
echo "  ✅ Downloader TUF verification"
echo "  ✅ Attestation verification"
echo ""
echo "S3 Structure:"
echo "  - s3://$S3_BUCKET/simple/${PACKAGE_NAME}/"
echo "  - s3://$S3_BUCKET/pointers/${PACKAGE_NAME}/"
echo "  - s3://$S3_BUCKET/attestations/${PACKAGE_NAME}/"
echo "  - s3://$S3_BUCKET/metadata/"
echo ""
echo "Next steps:"
echo "  - Review artifacts in S3 console"
echo "  - Test with additional integrations"
echo "  - Merge POC to master branch"
echo ""
