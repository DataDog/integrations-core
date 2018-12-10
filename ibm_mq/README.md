# Agent Check: IBM MQ

## Overview

This check monitors [IBM MQ][1].

## Setup

### Installation

The IBM MQ check is included in the [Datadog Agent][2] package.

In order to use the IBM MQ check, you need to install the [IBM MQ Client][3], unless the IBM MQ server is already installed on the box. Take note of where you installed it.

If you are using Linux, after the MQ Client is installed ensure the runtime linker can find the libraries. For example, using ldconfig:

```
# Put the library location in an ld configuration file.

sudo sh -c "echo /opt/mqm/lib64 > \
/etc/ld.so.conf.d/mqm64.conf"
sudo sh -c "echo /opt/mqm/lib > \
/etc/ld.so.conf.d/mqm.conf"

# Update the bindings.

sudo ldconfig
```

Alternately, update your LD_LIBRARY_PATH to include the location of the libraries. For example:

```
export LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib:$LD_LIBRARY_PATH
```

*Note*: Agent 6 uses Upstart or systemd to orchestrate the datadog-agent service. Environment variables may need to be added to the service configuration files at the default locations of /etc/init/datadog-agent.conf (Upstart) or /lib/systemd/system/datadog-agent.service (systemd). See documentation on Upstart or systemd for more information on how to configure these settings.

Here's an example of the configuration that's used for Systemd:

```yaml
[Unit]
Description="Datadog Agent"
After=network.target
Wants=datadog-agent-trace.service datadog-agent-process.service
StartLimitIntervalSec=10
StartLimitBurst=5

[Service]
Type=simple
PIDFile=/opt/datadog-agent/run/agent.pid
Environment="LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib"
User=dd-agent
Restart=on-failure
ExecStart=/opt/datadog-agent/bin/agent/agent run -p /opt/datadog-agent/run/agent.pid

[Install]
WantedBy=multi-user.target
```

Here's an example of the upstart config:

```
description "Datadog Agent"

start on started networking
stop on runlevel [!2345]

respawn
respawn limit 10 5
normal exit 0

# Logging to console from the Agent is disabled since the Agent already logs using file or
# syslog depending on its configuration. We make Upstart log what the process still outputs in order
# to log panics/crashes to /var/log/upstart/datadog-agent.log
console log
env DD_LOG_TO_CONSOLE=false
env LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib

setuid dd-agent

script
  exec /opt/datadog-agent/bin/agent/agent start -p /opt/datadog-agent/run/agent.pid
end script

post-stop script
  rm -f /opt/datadog-agent/run/agent.pid
end script
```

#### Permissions

Once you have the library set up, you'll need to create a user with the appropriate permissions.

### Configuration

1. Edit the `ibm_mq.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your ibm_mq performance data.
   See the [sample ibm_mq.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][6] and look for `ibm_mq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Service Checks

Ibm_mq does not include any service checks.

### Events

Ibm_mq does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][7].

[1]: https://www.ibm.com/products/mq
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://developer.ibm.com/messaging/mq-downloads/
[4]: https://github.com/DataDog/integrations-core/blob/master/ibm_mq/datadog_checks/ibm_mq/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
[8]: https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv
