# Agent Check: MapR

## Overview

This check monitors [MapR][1] 6.1+ through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The MapR check is included in the [Datadog Agent][2] package but requires additional setup operations.

#### Prerequisites

- [MapR monitoring][3] is running correctly.
- You have an available [MapR user][4] (with name, password, UID, and GID) with the 'consume' permission on the `/var/mapr/mapr.monitoring/metricstreams` stream. This may be an already existing user or a newly created user. If you want the user to be called `dd-agent`, create it before installing the Agent.
- You have generated a [service long-lived ticket][5] for this user that is readable by the `dd-agent` user.

Installation steps for each node:

1. [Install the Agent][2].
2. Install the library _mapr-streams-library_ with the following command:

    `sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib" --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python`.

    If you use Python 3 with Agent v7, replace `pip` with `pip3`.

3. Add `/opt/mapr/lib/` to your `/etc/ld.so.conf` (or a file in `/etc/ld.so.conf.d/`). This is required for the _mapr-streams-library_ used by the Agent to find the MapR shared libraries.
4. Reload the libraries by running `sudo ldconfig`.
5. Configure the integration by specifying the ticket location.

#### Additional notes

- If you don't have "security" enabled in the cluster, you can continue without a ticket.
- If your production environment does not allow compilation tools like gcc (required to build the mapr-streams-library), it is possible to generate a compiled wheel of the library on a development instance and distribute the compiled wheel to the production hosts. The development and production hosts have to be similar enough for the compiled wheel to be compatible. You can run `sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip wheel --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib" --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python` to create the wheel file on the development machine. Then, `sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install <THE_WHEEL_FILE>` on the production machine.
- If you use Python 3 with Agent v7, make sure to replace `pip` with `pip3` when installing the _mapr-streams-library_

### Configuration

#### Metric collection

1. Edit the `mapr.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your MapR performance data. See the [sample mapr.d/conf.yaml][6] for all available configuration options.
2. Set the `ticket_location` parameter in the config to the path of the long-lived ticket you created.
3. [Restart the Agent][7].

#### Log collection

MapR uses fluentD for logs. Use the [fluentD datadog plugin][8] to collect MapR logs. The following command downloads and installs the plugin into the right directory.

`curl https://raw.githubusercontent.com/DataDog/fluent-plugin-datadog/master/lib/fluent/plugin/out_datadog.rb -o /opt/mapr/fluentd/fluentd-<VERSION>/lib/fluentd-<VERSION>-linux-x86_64/lib/app/lib/fluent/plugin/out_datadog.rb`

Then update the `/opt/mapr/fluentd/fluentd-<VERSION>/etc/fluentd/fluentd.conf` with the following section.

```text
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
    dd_source mapr  # Sets "source: mapr" on every log to allow automatic parsing on Datadog.
    dd_tags "<KEY>:<VALUE>"
    service <YOUR_SERVICE_NAME>
    api_key <YOUR_API_KEY>
  </store>
```

Refer to [fluent_datadog_plugin][8] documentation for more details about the options you can use.

### Validation

[Run the Agent's status subcommand][9] and look for `mapr` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of default metrics provided by this integration.

### Service Checks

- `mapr.can_connect`:
  Returns `CRITICAL` if the Agent fails to connect and subscribe to the stream topic, `OK` otherwise.

### Events

The MapR check does not include any events.

## Troubleshooting

- **The Agent is on a crash loop after configuring the MapR integration**

  There have been a few cases where the C library within _mapr-streams-python_ segfaults because of permissions issues. Make sure the `dd-agent` user has read permission on the ticket file, that the `dd-agent` user is able to run maprcli commands when the MAPR_TICKETFILE_LOCATION environment variable points to the ticket.

- **The integration seems to work correctly but doesn't send any metric**.

  Make sure to let the Agent run for at least a couple of minutes, as the integration pulls data from a topic and MapR needs to push data into that topic.
  If that doesn't help, but running the Agent manually with `sudo` shows data, this is a problem with permissions. Double check everything. The `dd-agent` Linux user should be able to use a locally stored ticket, allowing it to run queries against MapR as user X (which may or may not be `dd-agent` itself). Additionally, user X needs to have the `consume` permission on the `/var/mapr/mapr.monitoring/metricstreams` stream.

- **You see the message `confluent_kafka was not imported correctly ...`**

  The Agent embedded environment was not able to run the command `import confluent_kafka`. This means that either the _mapr-streams-library_ was not installed inside the embedded environment, or that it can't find the mapr-core libraries. The error message should give more details.

Need more help? Contact [Datadog support][11].

[1]: https://mapr.com
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://mapr.com/docs/61/AdministratorGuide/Monitoring.html
[4]: https://mapr.com/docs/61/AdministratorGuide/c-managing-users-and-groups.html
[5]: https://mapr.com/docs/61/SecurityGuide/GeneratingServiceTicket.html
[6]: https://github.com/DataDog/integrations-core/blob/master/mapr/datadog_checks/mapr/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://www.rubydoc.info/gems/fluent-plugin-datadog
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/mapr/metadata.csv
[11]: https://docs.datadoghq.com/help/
