# Oracle Integration

## Overview

Get metrics from Oracle Database servers in real time to:

* Visualize and monitor Oracle Database service status.
* Be notified about Oracle Database cluster failovers and events.

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

From this point we'll need to make sure the relevant Oracle libraries are in the `LD_LIBRARY_PATH`:

```
if [ ! -e $ORACLE_HOME/libclntsh.so ]; then ln -s $ORACLE_HOME/libclntsh.so.12.1 $ORACLE_HOME/libclntsh.so; fi
echo "$ORACLE_HOME" | sudo tee /etc/ld.so.conf.d/oracle_instantclient.conf
sudo ldconfig
```

That should make the Oracle `instantclient` dynamic libs be reachable in the host system `LD_LIBRARY_PATH` and the python package `cx_Oracle`.

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

The Oracle check is currently compatible with the Linux and darwin-based OS

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv) for a list of metrics provided by this integration.

### Events
The Oracle Database check does not include any event at this time.

### Service Checks
The Oracle Database check does not include any service check at this time.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
