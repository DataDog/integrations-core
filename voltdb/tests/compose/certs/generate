#!/bin/sh -ex

CERTS_DIR="voltdb/tests/compose/certs"
mkdir -p $CERTS_DIR

KEYSTORE="$CERTS_DIR/voltdb_key.jks"
TRUSTSTORE="$CERTS_DIR/voltdb_trust.jks"
PASSWORD="tlspass"
ALIAS="voltdb"
VALIDITY="36500"  # 100 years.
TMP_REQ_FILE="$CERTS_DIR/server.csr"
TMP_CERT_FILE="$CERTS_DIR/server.cert"
TMP_P12_FILE="$CERTS_DIR/cert.p12"
CA_FILE="$CERTS_DIR/ca.pem"
CLIENT_CERT_FILE="$CERTS_DIR/client.pem"

# Remove any existing files.
rm -f $KEYSTORE $TRUSTSTORE $CA_FILE $CLIENT_CERT_FILE

## Generate server keystore and truststore.
keytool -genkeypair -keystore $KEYSTORE -storepass $PASSWORD -alias $ALIAS -dname "cn=localhost, ou=Datadog, o=Datadog, c=New York" -keyalg rsa -keysize 2048 -validity $VALIDITY -storetype jks
keytool -certreq -keystore $KEYSTORE -storepass $PASSWORD -alias $ALIAS -keyalg rsa -file $TMP_REQ_FILE
keytool -gencert -keystore $KEYSTORE -storepass $PASSWORD -alias $ALIAS -infile $TMP_REQ_FILE -outfile $TMP_CERT_FILE -validity $VALIDITY -ext "san=dns:localhost"
keytool -import -keystore $KEYSTORE -storepass $PASSWORD -alias $ALIAS -noprompt -file $TMP_CERT_FILE
keytool -import -keystore $TRUSTSTORE -storepass $PASSWORD -alias $ALIAS -storetype jks -noprompt -file $TMP_CERT_FILE

# Export CA file.
keytool -exportcert -file $CA_FILE -keystore $TRUSTSTORE -storepass $PASSWORD -alias $ALIAS -rfc

# Export client certificate.
keytool -importkeystore -srckeystore $KEYSTORE -srcstoretype jks -srcstorepass $PASSWORD -destkeystore $TMP_P12_FILE -deststoretype pkcs12 -deststorepass $PASSWORD -srcalias $ALIAS
# -nodes = no DES = don't encrypt private key.
openssl pkcs12 -nodes -in $TMP_P12_FILE -out $CLIENT_CERT_FILE -password pass:$PASSWORD -passout pass:$PASSWORD

# Cleanup.
rm $TMP_REQ_FILE $TMP_CERT_FILE $TMP_P12_FILE
