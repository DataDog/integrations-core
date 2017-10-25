# Oracle Integration

## Overview

Get metrics from Oracle Database servers in real time to visualize and monitor availability and performance.

## Setup
### Installation

Install the `dd-check-oracle` package manually or with your favorite configuration manager

In order to use the Oracle integration you must install Oracle's `instantclient` libraries by following the instructions below.  Due to licensing restrictions we are unable to include this library in our agent.

You may download `instantclient` directly from Oracle [here](https://www.oracle.com/technetwork/database/features/instant-client/index.html).

The steps to set up `instantclient` to work with the integration would typically be:

```
mkdir -p /opt/oracle/ && cd /opt/oracle/
# Download Oracle Instant Client (example dir: /opt/oracle)
unzip /opt/oracle/instantclient-basic-linux.x64-12.1.0.2.0.zip
unzip /opt/oracle/instantclient-sdk-linux.x64-12.1.0.2.0.zip
export ORACLE_HOME=/opt/oracle/instantclient/
```

From this point we'll need to ensure that relevant Oracle libraries are in the `LD_LIBRARY_PATH`:

```
if [ ! -e $ORACLE_HOME/libclntsh.so ]; then ln -s $ORACLE_HOME/libclntsh.so.12.1 $ORACLE_HOME/libclntsh.so; fi
echo "$ORACLE_HOME" | sudo tee /etc/ld.so.conf.d/oracle_instantclient.conf
sudo ldconfig
```

### Configuration

Edit the `oracle.yaml` file to point to your server and port, set the masters to monitor. See the [sample oracle.yaml](https://github.com/DataDog/integrations-core/blob/master/oracle/conf.yaml.default) for all available configuration options.

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        oracle
        -----------
          - instance #0 [OK]
          - Collected 18 metrics, 0 events & 1 service checks

### Compatibility

The Oracle check is currently compatible with Linux and macOS.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv) for a list of metrics provided by this integration.

### Events
The Oracle Database check does not include any events at this time.

### Service Checks
The Oracle Database integration includes the service check `oracle.can_connect` which will verify the database is available and accepting connections.
