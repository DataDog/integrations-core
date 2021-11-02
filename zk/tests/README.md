# Quick Start

The Zookeeper `ddev` environment has the option to have SSL enabled. SSL client and server test certificates can be found 
within `tests/compose`. Sometimes, there might be issues with these certs and need to be reset. This guide goes through 
the steps to generate new certs, since Zookeeper’s server does not use the widely-used `PEM` format for certs, and it 
instead relies on the concept of `keystore` and `truststore`. A `keystore` contains the private key and the public cert 
of a client/server, and the `truststore` contains the public certs of whoever the client/server trusts.

## Generate server `keystore`
```shell
keytool -genkey -alias server \
        -keyalg RSA \
        -keypass testpass \
        -storepass testpass \
        -keystore sample_keystore.jks 
```

This generates a `sample_keystore.jks` file with password `testpass` and alias `server`. This `keystore` contains the 
public cert and private key of the server. You will be prompted to input server name, organizational unit, organization, 
locality, state, and country code, but you only need to input the server name. For our purposes, enter `localhost` for 
the server name.

## Export server cert to `CER` file

```shell
keytool -export -alias server \
        -storepass testpass \
        -file server.cer \
        -keystore sample_keystore.jks
```

This generates a `CER` file called `server.cer`, which will be the actual server certificate.

## Import server cert to server `truststore`

```shell
keytool -import -v -trustcacerts \
        -alias server \
        -file server.cer \
        -keystore sample_truststore.jks \
        -keypass testpass \
        -storepass testpass
```
This generates `sample_truststore.jks` with password `testpass`. The server cert from the `sample_keystore.jks` is placed 
into this `truststore` because the server should be trusted by the server itself. Normally, `truststore` contains the CA
certs of trusted authorities. But in testing, we will just self-sign this.

## Generate client cert and private key

```shell
openssl req -x509 -newkey rsa:4096 \
            -keyout private_key.pem \
            -out cert.pem \
            -sha256 \
            -days 365
```
This generates a private.key and cert.pem file for the client. Again, you will be prompted to input server name, organizational 
unit, organization, locality, state, and country code, but you only need to input the server name. Enter localhost for 
the server name.

## Import client cert into server `truststore`

```shell
keytool -import -v \
        -trustcacerts \
        -alias client \
        -file cert.pem \
        -keystore sample_truststore.jks \
        -keypass testpass \
        -storepass testpass
```
This puts the client `cert.pem` into the server `sample_truststore.jks` file, so that the client cert will be trusted by
the server. 

After all of these commands are run, replace the `tests/compose/client` and `tests/compose/server` certs with the newly 
generated ones. Happy testing!