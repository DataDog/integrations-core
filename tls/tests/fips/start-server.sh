#!/bin/bash

if [ ! -f /etc/ssl/certs/server.crt ] || [ ! -f /etc/ssl/private/server.key ]; then
    echo "Generating self-signed certificate..."
    mkdir -p /etc/ssl/private
    openssl req -x509 -newkey rsa:2048 -keyout /etc/ssl/private/server.key -out /etc/ssl/certs/server.crt -days 365 -nodes -subj "/CN=localhost"
fi

CIPHER=$1

echo "Starting OpenSSL server on port 443 with cipher $CIPHER..."
openssl s_server \
    -accept 443 \
    -cert /etc/ssl/certs/server.crt \
    -key /etc/ssl/private/server.key \
    -cipher $CIPHER \
    -no_tls1_3 \
    -WWW
