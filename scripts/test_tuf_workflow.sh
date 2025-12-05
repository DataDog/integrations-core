#!/bin/bash
# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Integration test script for TUF wheel upload workflow
# This script tests the complete workflow: build -> upload -> sign

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
INTEGRATION="${1:-postgres}"
S3_BUCKET="test-public-integration-wheels"
S3_REGION="eu-north-1"

echo -e "${GREEN}=== Testing TUF Upload Workflow ===${NC}"
echo "Integration: $INTEGRATION"
echo "S3 Bucket: $S3_BUCKET"
echo ""

# Check if integration exists
if [ ! -d "$INTEGRATION" ]; then
    echo -e "${RED}Error: Integration directory '$INTEGRATION' not found${NC}"
    echo "Usage: $0 [integration_name]"
    echo "Example: $0 postgres"
    exit 1
fi

# Step 1: Build
echo -e "${YELLOW}Step 1: Building $INTEGRATION...${NC}"
ddev release build "$INTEGRATION"

# Verify pointer file was created
POINTER_FILE=$(find "$INTEGRATION/dist" -name "*.pointer" | head -n 1)
if [ -z "$POINTER_FILE" ]; then
    echo -e "${RED}Error: No pointer file found in $INTEGRATION/dist/${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build successful${NC}"
echo "  Pointer file: $POINTER_FILE"

# Show pointer file contents
echo "  Pointer contents:"
cat "$POINTER_FILE" | sed 's/^/    /'
echo ""

# Step 2: Upload
echo -e "${YELLOW}Step 2: Uploading $INTEGRATION to S3...${NC}"
echo "Note: ddev will automatically use aws-vault if credentials are not available"
echo ""

ddev release upload "$INTEGRATION" --public

echo -e "${GREEN}✓ Upload successful${NC}"
echo ""

# Step 3: Sign
echo -e "${YELLOW}Step 3: Signing TUF metadata...${NC}"
ddev release sign --generate-keys

echo -e "${GREEN}✓ Sign successful${NC}"
echo ""

# Step 4: Verify S3 contents
echo -e "${YELLOW}Step 4: Verifying S3 structure...${NC}"

# Function to check S3 path exists
check_s3_path() {
    local path=$1
    local description=$2

    if aws s3 ls "s3://${S3_BUCKET}/${path}" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $description"
        aws s3 ls "s3://${S3_BUCKET}/${path}" | sed 's/^/    /'
    else
        echo -e "${RED}✗${NC} $description - NOT FOUND"
        return 1
    fi
}

echo ""
echo "Checking uploaded files:"

# Get package name (convert folder name to package name)
PACKAGE_NAME=$(ddev release build "$INTEGRATION" --help 2>&1 | grep -o "datadog-[a-z_-]*" | head -n 1 || echo "datadog-$INTEGRATION")

check_s3_path "simple/${PACKAGE_NAME}/" "Wheel files in simple/${PACKAGE_NAME}/"
echo ""

check_s3_path "pointers/${PACKAGE_NAME}/" "Pointer files in pointers/${PACKAGE_NAME}/"
echo ""

check_s3_path "simple/${PACKAGE_NAME}/index.html" "Package index at simple/${PACKAGE_NAME}/index.html"
echo ""

check_s3_path "simple/index.html" "Root index at simple/index.html"
echo ""

check_s3_path "metadata/" "TUF metadata files"
echo ""

# Step 5: Verify TUF metadata
echo -e "${YELLOW}Step 5: Verifying TUF metadata integrity...${NC}"

# Download metadata files for inspection
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

aws s3 cp "s3://${S3_BUCKET}/metadata/root.json" "$TEMP_DIR/root.json" &> /dev/null
aws s3 cp "s3://${S3_BUCKET}/metadata/targets.json" "$TEMP_DIR/targets.json" &> /dev/null
aws s3 cp "s3://${S3_BUCKET}/metadata/snapshot.json" "$TEMP_DIR/snapshot.json" &> /dev/null
aws s3 cp "s3://${S3_BUCKET}/metadata/timestamp.json" "$TEMP_DIR/timestamp.json" &> /dev/null

# Check JSON validity
for file in root targets snapshot timestamp; do
    if python3 -m json.tool "$TEMP_DIR/${file}.json" &> /dev/null; then
        echo -e "${GREEN}✓${NC} ${file}.json is valid JSON"
    else
        echo -e "${RED}✗${NC} ${file}.json is invalid JSON"
        exit 1
    fi
done

# Check that root.json has signatures
if grep -q '"signatures"' "$TEMP_DIR/root.json"; then
    SIGNATURE_COUNT=$(grep -c '"keyid"' "$TEMP_DIR/root.json" || echo "0")
    echo -e "${GREEN}✓${NC} root.json has $SIGNATURE_COUNT signature(s)"
else
    echo -e "${RED}✗${NC} root.json is missing signatures"
    exit 1
fi

# Check that targets.json includes our pointer
if grep -q "$PACKAGE_NAME" "$TEMP_DIR/targets.json"; then
    echo -e "${GREEN}✓${NC} targets.json includes $PACKAGE_NAME"
else
    echo -e "${RED}✗${NC} targets.json does not include $PACKAGE_NAME"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Workflow Complete ===${NC}"
echo ""
echo "Summary:"
echo "  ✓ Wheel built with pointer file"
echo "  ✓ Files uploaded to S3 with organized structure"
echo "  ✓ Simple indexes generated (PyPI-compatible)"
echo "  ✓ TUF metadata signed and uploaded"
echo "  ✓ All verification checks passed"
echo ""
echo "S3 Bucket Structure:"
echo "  s3://${S3_BUCKET}/"
echo "    ├── simple/${PACKAGE_NAME}/"
echo "    │   ├── index.html"
echo "    │   └── *.whl"
echo "    ├── pointers/${PACKAGE_NAME}/"
echo "    │   └── *.pointer"
echo "    └── metadata/"
echo "        ├── root.json"
echo "        ├── targets.json"
echo "        ├── snapshot.json"
echo "        └── timestamp.json"
echo ""
echo -e "${GREEN}POC Test Successful!${NC}"
