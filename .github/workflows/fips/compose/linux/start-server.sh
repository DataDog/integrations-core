#!/bin/bash

if [ ! -f ./ca.crt ] || [ ! -f ./ca.key ]; then
    echo "Generating self-signed certificate..."
    openssl req -x509 -newkey rsa:2048 -keyout ca.key -out ca.crt -days 365 -nodes -subj "/CN=localhost"
fi

CIPHER=$1

echo "Starting OpenSSL server on port 443 with cipher $CIPHER..."
openssl s_server \
    -accept 443 \
    -cert ca.crt \
    -key ca.key \
    -cipher $CIPHER \
    -no_tls1_3 \
    -WWW
