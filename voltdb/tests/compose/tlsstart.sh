#!/bin/sh -ex

# Must match paths in deployment-tls.xml
SSL_LOCAL="/etc/ssl/local"
KEYSTORE="$SSL_LOCAL/voltdb.keystore"
TRUSTSTORE="$SSL_LOCAL/voltdb.truststore"
mkdir -p $SSL_LOCAL

# Shared with host.
OUTPUT_DIR="/tmp/tlsoutput"
mkdir -p $OUTPUT_DIR

PASSWORD="tlspass"
ALIAS="voltdb"
REQ_FILE="server.csr"
CERT_FILE="server.pem"
CLIENT_CERT_PEM_FILE="$OUTPUT_DIR/client.pem"

# Inspired by: https://docs.voltdb.com/UsingVoltDB/SecuritySSL.php

# Generate keystore with password.
keytool -genkey -keystore $KEYSTORE -storetype pkcs12 -storepass $PASSWORD -alias $ALIAS -dname "cn=localhost, ou=Unknown, o=Unknown, c=Unknown" -keyalg rsa -validity 365 -keysize 2048

# Create key signing request.
keytool -certreq -keystore $KEYSTORE -storepass $PASSWORD -alias $ALIAS -keyalg rsa -file $REQ_FILE

# Create and sign certificate.
keytool -gencert -keystore $KEYSTORE -storetype pkcs12 -storepass $PASSWORD -alias $ALIAS -infile $REQ_FILE -outfile $CERT_FILE -validity 365

# Import certificate into keystore.
keytool -import -keystore $KEYSTORE -storetype pkcs12 -storepass $PASSWORD -alias $ALIAS -noprompt -file $CERT_FILE

# Create associated truststore.
keytool -import -keystore $TRUSTSTORE -storetype pkcs12 -storepass $PASSWORD -alias $ALIAS -noprompt -file $CERT_FILE

# Export client certificate (for the Agent to use).
# See: https://stackoverflow.com/questions/652916/converting-a-java-keystore-into-pem-format
# Also make sure it doesn't have a password (see: https://serverfault.com/a/515842).
openssl pkcs12 -in $KEYSTORE -out $CLIENT_CERT_PEM_FILE -password pass:$PASSWORD -passout pass:temp
openssl rsa -in $CLIENT_CERT_PEM_FILE -passin pass:temp -out $CLIENT_CERT_PEM_FILE

# Run usual entrypoint (provided by base VoltDB image).
exec ./docker-entrypoint.sh
