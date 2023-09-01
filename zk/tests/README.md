## Overview

You can enable SSL for your Zookeeper `ddev` environment. The SSL client and server test certificates can be found within `tests/compose`. There may sometimes be issues with these certs and they need to be reset. 

This guide covers how to generate new certificates. Zookeeper’s server does not use the widely-used `PEM` format for certs—instead, it relies on `keystore` and `truststore` concepts. A `keystore` contains the private key and the public cert of a client/server. A `truststore` contains the public certs of whomever the client/server trusts.

## Generate server `keystore`
```shell
keytool -genkey -alias server \
        -keyalg RSA \
        -keypass testpass \
        -storepass testpass \
        -keystore sample_keystore.jks \
        -validity 3650
```

This generates a `sample_keystore.jks` file with password `testpass` and alias `server`. This `keystore` contains the public cert and private key of the server. 

While you are prompted to input the server name, organizational unit, organization, locality, state, and country code, you only need to input the server name. Enter `localhost` for the server name.

## Export server cert to `CER` file

```shell
keytool -export -alias server \
        -storepass testpass \
        -file server.cer \
        -keystore sample_keystore.jks
```

This generates a `CER` file called `server.cer`, which is the actual server certificate.

## Import server cert to server `truststore`

```shell
keytool -import -v -trustcacerts \
        -alias server \
        -file server.cer \
        -keystore sample_truststore.jks \
        -keypass testpass \
        -storepass testpass \
        -validity 3650
```

This generates a `sample_truststore.jks` file with password `testpass`. The server cert from the `sample_keystore.jks` is placed into this `truststore` because the server trusts itself. Normally, `truststore` contains the CA certs of trusted authorities. In testing, we self-sign this.

## Generate client cert and private key

```shell
openssl req -x509 -newkey rsa:4096 \
            -keyout private_key.pem \
            -out cert.pem \
            -sha256 \
            -days 3650
```

This generates a `private_key.pem` and `cert.pem` file for the client. When it asks for PEM pass phrase, enter `testpass`.

While you are prompted to input the server name, organizational unit, organization, locality, state, and country code, you only need to input the server name. Enter `localhost` for the server name.

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

This puts the client `cert.pem` in the server `sample_truststore.jks` file so the server trusts the client cert. 

## Convert `server.cer` into `ca_cert.pem`

```shell
openssl x509 -inform der -in server.cer -out ca_cert.pem
```

This converts the `CER` file into a `PEM` file to make it easier to use in testing.


After running all these commands, replace the `tests/compose/client` and `tests/compose/server` certs with your newly generated certificates. 