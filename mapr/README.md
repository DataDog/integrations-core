# Agent Check: MapR

## Overview

This check monitors [MapR][1] 6.1+ through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The MapR check is included in the [Datadog Agent][2] package but requires additional setup operations.

Prerequisites:
- [MapR Monitoring][16] needs to be running correctly.
- You need an available [MapR user][10] (same name, password, uid and gid) with the 'consume' permission on the `/var/mapr/mapr.monitoring/metricstreams` stream. This may be an already existing user or a newly created user. If you want the user user to be called `dd-agent`, you have to create it before installing the agent.
- You need to generate a [service long-lived ticket][8] for this user that is readable by the `dd-agent` user.


Installation steps for each node:
1. [Install][2] the Agent
2. Install the library *mapr-streams-library* with the following command: `sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib" --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python`. If you use Python 3 with Agent 6, replace `pip` by `pip3`.
3. Add `/opt/mapr/lib/` to your `/etc/ld.so.conf` (or a file in `/etc/ld.so.conf.d/`). This is required for the *mapr-streams-library* used by the Agent to find the MapR shared libraries.
4. Reload the libraries by running `sudo ldconfig`
5. Configure the integration by specifying the ticket location.


### Additional notes

- If you don't have "security" enabled in the cluster, you can continue without a ticket.

- If your production environment does not allow compilation tools like gcc (required to build the mapr-streams-library), it is possible to generate a compiled wheel of the library on a development instance and distribute the compiled wheel to the production hosts. The development and production hosts have to be similar enough for the compiled wheel to be compatible.
You can run `sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip wheel --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib" --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python` to create the wheel file on the development machine.
And then `sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install <THE_WHEEL_FILE>` on the production machine.

- If you use python3 with Agent6, make sure to replace `pip` by `pip3` when installing the *mapr-streams-library*

### Troubleshooting

- The agent is on a crash loop after configuring the MapR integration
There are been a few cases where the C library within *mapr-streams-python* is segfaulting and it was all explained by permissions issues. Make sure the `dd-agent` user has read permission on the ticket file, that the `dd-agent` user is able to run maprcli commands when the MAPR_TICKETFILE_LOCATION environment variable points to the ticket.

- The integration seems to work correctly but doesn't send any metric.
First make sure to let the agent run for at least a couple of minutes as the integration pulls data from a topic and MapR needs to push data into that topic.
If that doesn't help, but running the agent manually with `sudo` shows data this is once again some permission issues. Double check everything, in the end the `dd-agent` Linux user should be able to use a locally stored ticket allowing it to run queries against MapR as user X (which may or may not be `dd-agent` itself). And user X needs to have the `consume` permission on the `/var/mapr/mapr.monitoring/metricstreams` stream.

- You see the message `confluent_kafka was not imported correctly ...`
The agent embedded environment was not able to run the command `import confluent_kafka`. This means that either the *mapr-streams-library* was not installed inside the embedded environment, or that it can't find the mapr-core libraries. The error message should give more details.

### Configuration
#### Metric collection

1. Edit the `mapr.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your MapR performance data. See the [sample mapr.d/conf.yaml][3] for all available configuration options.
2. Set the `ticket_location` parameter in the config to the path of the long-lived ticket you created.
3. [Restart the Agent][4].

#### Log collection

MapR uses fluentD for logs. Use the [fluentD datadog plugin][11] to collect MapR logs.
The following command downloads and installs the plugin into the right directory.

`curl https://raw.githubusercontent.com/DataDog/fluent-plugin-datadog/master/lib/fluent/plugin/out_datadog.rb -o /opt/mapr/fluentd/fluentd-<VERSION>/lib/fluentd-<VERSION>-linux-x86_64/lib/app/lib/fluent/plugin/out_datadog.rb`

Then update the `/opt/mapr/fluentd/fluentd-<VERSION>/etc/fluentd/fluentd.conf` with the following section.

```
<match *>
  @type copy
  <store> # This section is here by default and sends the logs to ElasticCache for Kibana.
    @include /opt/mapr/fluentd/fluentd-<VERSION>/etc/fluentd/es_config.conf
    include_tag_key true
    tag_key service_name
  </store>
  <store> # This section also forwards all the logs to Datadog:
    @type datadog
    @id dd_agent
    include_tag_key true
    dd_source mapr
    dd_tags "<KEY>:<VALUE>"
    service <YOUR_SERVICE_NAME>
    api_key <YOUR_API_KEY>
  </store>
```

Refer to [fluent_datadog_plugin][11] documentation for more details about the options you can use.


### Validation

[Run the Agent's status subcommand][5] and look for `mapr` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][13] for a list of default metrics provided by this integration.

### Service Checks

- `mapr.can_connect`:
Returns `CRITICAL` if the Agent fails to connect and subscribe to the stream topic, `OK` otherwise.

### Events

The MapR check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://mapr.com
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/mapr/datadog_checks/mapr/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help
[7]: https://mapr.com/docs/61/MapR_Streams/MapRStreamsPythonExample.html
[8]: https://mapr.com/docs/61/SecurityGuide/GeneratingServiceTicket.html
[9]: https://mapr.com/docs/60/MapR_Streams/MapRStreamCAPISetup.html
[10]: https://mapr.com/docs/61/AdministratorGuide/c-managing-users-and-groups.html
[11]: https://www.rubydoc.info/gems/fluent-plugin-datadog
[12]: https://mapr.com/docs/61/AdvancedInstallation/SettingUptheClient-install-mapr-client.html
[13]: https://github.com/DataDog/integrations-core/blob/master/mapr/metadata.csv
[14]: http://upstart.ubuntu.com/cookbook/#environment-variables
[15]: https://www.freedesktop.org/software/systemd/man/systemd.service.html#Command%20lines
[16]: https://mapr.com/docs/61/AdministratorGuide/Monitoring.html
