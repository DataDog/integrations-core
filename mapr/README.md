# Agent Check: MapR

## Overview

This check monitors [MapR][1] 6.1+ through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The MapR check is included in the [Datadog Agent][2] package but requires additional setup operations.

1. Add `/opt/mapr/lib/` to your `ld.so.conf` file. The Agent uses the *mapr-streams-python* library which requires access to some shared libraries.
2. Create a password for the `dd-agent` user, then add this user to every node of the cluster with the same `UID`/`GID` so it is recognized by MapR. See [Managing users and groups][10] for additional details.
3. Install the Agent on every host you want to monitor.
4. Generate a [long-lived ticket][8] for the `dd-agent` user.
5. Make sure the ticket is readable by the `dd-agent` user.


### Configuration
#### Metric collection

1. Edit the `mapr.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your MapR performance data. See the [sample mapr.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

#### Log collection

MapR uses fluentD for logs. Use the [fluent datadog plugin][11] to collect MapR logs.
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
  <store> # This new section also forwards the logs to Datadog
    @type datadog
    @id dd_agent
    include_tag_key true
    dd_source mapr
    dd_tags "flo:test"
    service <YOUR_SERVICE_NAME>
    api_key <YOUR_API_KEY>
  </store>
```

Refer to [fluent_datadog_plugin][11] documentation for more details about the option you can use.


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
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
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
