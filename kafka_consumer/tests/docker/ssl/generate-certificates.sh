#!/usr/bin/env bash

set -eu

export COUNTRY=US
export STATE=
export ORGANIZATION_UNIT=ServiceUsers
export CITY=
export PASSWORD=secret
export CN=kafka-admin

validity=3650
defaultTruststoreName="kafka.truststore.jks"
truststoreWorkDir="truststore"
keystoreWorkDir="keystore"
caKey="ca-cert"
keystoreSignInRequest="cert-file"
keystoreSignRequestSrl="ca-cert.srl"
keystoreSignedCert="cert-signed"

country=$COUNTRY
state=$STATE
OU=$ORGANIZATION_UNIT
CN=$CN
location=$CITY
password=$PASSWORD

function file_exists_and_exit() {
echo "'$1' cannot exist. Move or delete it before"
echo "re-running this script."
exit 1
}

if [ -e "$keystoreWorkDir" ]; then
  file_exists_and_exit $keystoreWorkDir
fi

if [ -e "$caKey" ]; then
  file_exists_and_exit $caKey
fi

if [ -e "$keystoreSignInRequest" ]; then
  file_exists_and_exit $keystoreSignInRequest
fi

if [ -e "$keystoreSignRequestSrl" ]; then
  file_exists_and_exit $keystoreSignRequestSrl
fi

if [ -e "$keystoreSignedCert" ]; then
  file_exists_and_exit $keystoreSignedCert
fi

echo "Welcome to the Kafka SSL keystore and trust store generator script."

truststoreFile=""
truststorePrivateKey=""

if [ ! -e "$truststoreWorkDir" ]; then
  mkdir $truststoreWorkDir
  echo
  echo "OK, we'll generate a trust store and associated private key."
  echo
  echo "First, the private key."
  echo

  openssl req -new -x509 -keyout $truststoreWorkDir/ca-key \
    -out $truststoreWorkDir/ca-cert -days $validity -nodes \
    -subj "/C=$country/ST=$state/L=$location/O=$OU/CN=$CN"

  truststorePrivateKey="$truststoreWorkDir/ca-key"

  echo
  echo "Two files were created:"
  echo " - $truststoreWorkDir/ca-key -- the private key used later to"
  echo " sign certificates"
  echo " - $truststoreWorkDir/ca-cert -- the certificate that will be"
  echo " stored in the trust store in a moment and serve as the certificate"
  echo " authority (CA). Once this certificate has been stored in the trust"
  echo " store, it will be deleted. It can be retrieved from the trust store via:"
  echo " $ keytool -keystore <trust-store-file> -export -alias CARoot -rfc"

  echo
  echo "Now the trust store will be generated from the certificate."
  echo

  keytool -keystore $truststoreWorkDir/$defaultTruststoreName \
    -alias CARoot -import -file $truststoreWorkDir/ca-cert \
    -noprompt -dname "C=$country, ST=$state, L=$location, O=$OU, CN=$CN" -keypass $password -storepass $password

  truststoreFile="$truststoreWorkDir/$defaultTruststoreName"

  echo
  echo "$truststoreWorkDir/$defaultTruststoreName was created."

  # don't need the cert because it's in the trust store.
  rm $truststoreWorkDir/$caKey

  echo
  echo "Continuing with:"
  echo " - trust store file: $truststoreFile"
  echo " - trust store private key: $truststorePrivateKey"

else
  truststorePrivateKey="$truststoreWorkDir/ca-key"
  truststoreFile="$truststoreWorkDir/$defaultTruststoreName"
fi

mkdir $keystoreWorkDir

for kafkaHost in kafka1 kafka2 localhost; do
  echo
  echo "Now, a keystore will be generated. Each broker and logical client needs its own"
  echo "keystore. This script will create only one keystore. Run this script multiple"
  echo "times for multiple keystores."
  echo
  echo " NOTE: currently in Kafka, the Common Name (CN) does not need to be the FQDN of"
  echo " this host. However, at some point, this may change. As such, make the CN"
  echo " the FQDN. Some operating systems call the CN prompt 'first / last name'"

  # To learn more about CNs and FQDNs, read:
  # https://docs.oracle.com/javase/7/docs/api/javax/net/ssl/X509ExtendedTrustManager.html

  keystoreFileName="$kafkaHost.server.keystore.jks"

  keytool -keystore $keystoreWorkDir/"$keystoreFileName" \
    -alias localhost -validity $validity -genkey -keyalg RSA \
    -noprompt -dname "C=$country, ST=$state, L=$location, O=$OU, CN=localhost" \
    -keypass $password -storepass $password

  echo
  echo "'$keystoreWorkDir/$keystoreFileName' now contains a key pair and a"
  echo "self-signed certificate. Again, this keystore can only be used for one broker or"
  echo "one logical client. Other brokers or clients need to generate their own keystores."

  echo
  echo "Fetching the certificate from the trust store and storing in $caKey."
  echo

  keytool -keystore $truststoreFile -export -alias CARoot -rfc -file $caKey -keypass $password -storepass $password

  echo
  echo "Now a certificate signing request will be made to the keystore."
  echo
  keytool -keystore $keystoreWorkDir/"$keystoreFileName" -alias localhost \
    -certreq -file $keystoreSignInRequest -keypass $password -storepass $password

  echo
  echo "Now the trust store's private key (CA) will sign the keystore's certificate."
  echo
  openssl x509 -req -CA $caKey -CAkey $truststorePrivateKey \
    -in $keystoreSignInRequest -out $keystoreSignedCert \
    -days $validity -CAcreateserial -sha256
  # creates $keystoreSignRequestSrl which is never used or needed.

  echo
  echo "Now the CA will be imported into the keystore."
  echo
  keytool -keystore $keystoreWorkDir/"$keystoreFileName" -alias CARoot \
    -import -file $caKey -keypass $password -storepass $password -noprompt
    rm $caKey # delete the trust store cert because it's stored in the trust store.

  echo
  echo "Now the keystore's signed certificate will be imported back into the keystore."
  echo
  keytool -keystore $keystoreWorkDir/"$keystoreFileName" -alias localhost -import \
    -file $keystoreSignedCert -keypass $password -storepass $password

  echo
  echo "All done!"
  echo
  echo "Deleting intermediate files. They are:"
  echo " - '$keystoreSignRequestSrl': CA serial number"
  echo " - '$keystoreSignInRequest': the keystore's certificate signing request"
  echo " (that was fulfilled)"
  echo " - '$keystoreSignedCert': the keystore's certificate, signed by the CA, and stored back"
  echo " into the keystore"

  rm $keystoreSignRequestSrl
  rm $keystoreSignInRequest
  rm $keystoreSignedCert
done


