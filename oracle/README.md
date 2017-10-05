# Oracle Integration

## Overview

Get metrics from oracle service in real time to:

* Visualize and monitor oracle states
* Be notified about oracle failovers and events.

## Setup
### Installation

Install the `dd-check-oracle` package manually or with your favorite configuration manager

We cannot ship the oracle `instantclient` libraries with the agent or the standalone check due to licensing issues. Although the required `cx_Oracle` python library will be bundled, you will still need to install the `instantclient` for it to work (hard-requirement). The steps to do so would trypically be:

```
mkdir -p /opt/oracle/ && cd /opt/oracle/
# Download Oracle Instant Client (example dir: /opt/oracle)
unzip /opt/oracle/instantclient-basic-linux.x64-12.1.0.2.0.zip
unzip /opt/oracle/instantclient-sdk-linux.x64-12.1.0.2.0.zip
export ORACLE_HOME=/opt/oracle/instantclient/
```

From this point we'll need to make sure the relevant oracle libs are in the `LD_LIBRARY_PATH`:

```
if [ ! -e $ORACLE_HOME/libclntsh.so ]; then ln -s $ORACLE_HOME/libclntsh.so.12.1 $ORACLE_HOME/libclntsh.so; fi
echo "$ORACLE_HOME" | sudo tee /etc/ld.so.conf.d/oracle_instantclient.conf
sudo ldconfig
```

That should make the oracle `instantclient` dynamic libs be reachable in the host system `LD_LIBRARY_PATH` and the python package `cx_Oracle`.

Please do not hesitate to contact support or open an issue should you encounter any problems.

### Configuration

Edit the `oracle.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        oracle
        -----------
          - instance #0 [OK]
          - Collected 18 metrics, 0 events & 1 service checks

### Compatibility

The oracle check is currently compatible with the linux and darwin-based OS

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv) for a list of metrics provided by this integration.

### Events
The oracle check does not include any event at this time.

### Service Checks
The oracle check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)