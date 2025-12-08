#!/bin/bash
# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Script to make the test-public-integration-wheels bucket publicly accessible

set -e

BUCKET_NAME="test-public-integration-wheels"
REGION="eu-north-1"

echo "Configuring public access for bucket: $BUCKET_NAME"
echo ""

# Step 1: Remove block public access settings
echo "Step 1: Removing block public access settings..."
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
        "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

echo "✓ Public access settings updated"
echo ""

# Step 2: Apply bucket policy for public read access
echo "Step 2: Applying bucket policy for public read access..."

cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
    },
    {
      "Sid": "PublicListBucket",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
    --bucket "$BUCKET_NAME" \
    --policy file:///tmp/bucket-policy.json

rm /tmp/bucket-policy.json

echo "✓ Bucket policy applied"
echo ""

# Step 3: Verify configuration
echo "Step 3: Verifying configuration..."

# Test public access to a metadata file
TEST_URL="https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/metadata/root.json"
echo "Testing public access to: $TEST_URL"

if curl -f -s -o /dev/null -w "%{http_code}" "$TEST_URL" | grep -q "200"; then
    echo "✓ Public access verified successfully!"
else
    echo "⚠ Warning: Could not verify public access. This might be because no files exist yet."
fi

echo ""
echo "=== Configuration Complete ==="
echo ""
echo "Your bucket is now publicly accessible at:"
echo "  https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/"
echo ""
echo "To test access, try:"
echo "  curl https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com/metadata/root.json"
