#!/bin/bash

# Generate proper test certificates for Harbor integration tests
# This script creates a complete certificate chain with proper Authority Key Identifiers

set -e

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cert"
mkdir -p "$CERT_DIR"

echo "Generating test certificates in $CERT_DIR..."

# Generate CA private key
openssl genrsa -out "$CERT_DIR/ca.key" 4096

# Generate CA certificate with proper extensions
openssl req -new -x509 -days 3650 -key "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" \
    -subj "/C=US/ST=CA/L=San Francisco/O=Datadog/OU=Test/CN=Harbor Test CA" \
    -addext "basicConstraints=critical,CA:true" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -addext "subjectKeyIdentifier=hash" \
    -addext "authorityKeyIdentifier=keyid:always,issuer"

# Generate server private key
openssl genrsa -out "$CERT_DIR/server.key" 2048

# Generate server certificate signing request
openssl req -new -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" \
    -subj "/C=US/ST=CA/L=San Francisco/O=Datadog/OU=Test/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:harbor-core,DNS:harbor-registry,DNS:harbor-chartmuseum,IP:127.0.0.1,IP:0.0.0.0"

# Generate server certificate signed by CA
openssl x509 -req -days 365 -in "$CERT_DIR/server.csr" -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
    -CAcreateserial -out "$CERT_DIR/server.crt" \
    -extfile <(cat <<EOF
basicConstraints=CA:false
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
subjectAltName=DNS:localhost,DNS:harbor-core,DNS:harbor-registry,DNS:harbor-chartmuseum,IP:127.0.0.1,IP:0.0.0.0
EOF
)

# Create a combined certificate file for nginx
cat "$CERT_DIR/server.crt" "$CERT_DIR/ca.crt" > "$CERT_DIR/server-chain.crt"

# Create root.crt for registry service (same as ca.crt)
cp "$CERT_DIR/ca.crt" "$CERT_DIR/root.crt"

# Set proper permissions
chmod 600 "$CERT_DIR"/*.key
chmod 644 "$CERT_DIR"/*.crt
chmod 644 "$CERT_DIR"/*.csr

# Clean up temporary files
rm -f "$CERT_DIR/server.csr" "$CERT_DIR/ca.srl"

echo "Certificate generation complete!"
echo "Generated files:"
echo "  - CA Certificate: $CERT_DIR/ca.crt"
echo "  - Root Certificate (for registry): $CERT_DIR/root.crt"
echo "  - Server Certificate: $CERT_DIR/server.crt"
echo "  - Server Private Key: $CERT_DIR/server.key"
echo "  - Server Chain: $CERT_DIR/server-chain.crt"

echo ""
echo "To use these certificates:"
echo "1. Copy server-chain.crt and server.key to your nginx SSL configuration"
echo "2. Use ca.crt as the CA certificate for client verification"
echo "3. root.crt is automatically copied from ca.crt for registry service" 