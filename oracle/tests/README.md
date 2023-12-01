# Running docker e2e tests locally 

Before running e2e tests locally you need to `docker login container-registry.oracle.com` with valid credentials.

The credentials is the one used to login to https://container-registry.oracle.com/.

The image we are using is named `Oracle Database Enterprise Edition`.

# Testing on TCPS

## Regenerating Wallets

TCPS requires the client and server to use valid certs. Sometimes, these certs may need to be rotated. 

Use the following commands in the Oracle test environment (uncomment the java installation from the Dockerfile) to generate a new set of valid wallets and certs for the client and server:

```shell
export JAVA_HOME=/usr/lib/jvm/jre
mkdir -p server_wallet
mkdir -p client_wallet
orapki wallet create -wallet server_wallet -auto_login -pwd testpass123
orapki wallet create -wallet client_wallet -auto_login -pwd testpass123
orapki wallet add -wallet server_wallet -dn "CN=localhost" -keysize 4096 -self_signed -validity 3650 -pwd testpass123
orapki wallet add -wallet client_wallet -dn "CN=localhost" -keysize 4096 -self_signed -validity 3650 -pwd testpass123
orapki wallet export -wallet server_wallet -dn "CN=localhost" -cert server-cert.crt -pwd testpass123
orapki wallet export -wallet client_wallet -dn "CN=localhost" -cert client-cert.crt -pwd testpass123
orapki wallet add -wallet server_wallet -trusted_cert -cert client-cert.crt -pwd testpass123
orapki wallet add -wallet client_wallet -trusted_cert -cert server-cert.crt -pwd testpass123
cp server-cert.crt client_wallet/cert.pem
```

This creates the `server_wallet` and `client_wallet` directories which contain valid keys to access the database from the Datadog Agent.

After the keys are generated, place `server_wallet` in `oracle/tests/docker/server` and `client_wallet` in `oracle/tests/docker/client`. You can also place them within their respective Docker containers in the `$TNS_ADMIN` file path for both containers.  

As mentioned in the main README, you can verify that the keys and other configuration files are valid by using the `sqlplus` command included in the Oracle test environment: 

```shell
sqlplus datadog/Oracle123@alias
```

Note that `alias` is used in-place of the full DSN address. This is because `tnsnames.ora` adds `alias` to direct to the correct TCPS host and port. 

## Modifying `listener.ora`, `sqlnet.ora`, and `tnsnames.ora`

If you modify the `*.ora` configuration files in the Oracle test environment, make sure to restart the listener in order for changes to occur:

```shell
lsnrctl stop
lsnrctl start
```