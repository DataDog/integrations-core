# Fluentd Integration

![Fluentd Dashboard][1]

## Overview

Get metrics from Fluentd to:

- Visualize Fluentd performance.
- Correlate the performance of Fluentd with the rest of your applications.

## Setup

### Installation

The Fluentd check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Fluentd servers.

#### Prepare Fluentd

In your Fluentd configuration file, add a `monitor_agent` source:

```text
<source>
  @type monitor_agent
  bind 0.0.0.0
  port 24220
</source>
```

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `fluentd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your [Fluentd metrics](#metrics). See the [sample fluentd.d/conf.yaml][4] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param monitor_agent_url - string - required
     ## Monitor Agent URL to connect to.
     #
     - monitor_agent_url: http://example.com:24220/api/plugins.json
   ```

2. [Restart the Agent][5].

##### Log collection

You can use the [Datadog FluentD plugin][6] to forward the logs directly from FluentD to your Datadog account.

###### Add metadata to your logs

Proper metadata (including hostname and source) is the key to unlocking the full potential of your logs in Datadog. By default, the hostname and timestamp fields should be properly remapped with the [remapping for reserved attributes][7].

###### Source and custom tags

Add the `ddsource` attribute with [the name of the log integration][8] in your logs in order to trigger the [integration automatic setup][9] in Datadog.
[Host tags][10] are automatically set on your logs if there is a matching hostname in your [infrastructure list][11]. Use the `ddtags` attribute to add custom tags to your logs:

Setup Example:

```conf
  # Match events tagged with "datadog.**" and
  # send them to Datadog

<match datadog.**>
  @type datadog
  @id awesome_agent
  api_key <your_api_key>

  # Optional
  include_tag_key true
  tag_key 'tag'

  # Optional tags
  dd_source '<INTEGRATION_NAME>'
  dd_tags '<KEY1:VALUE1>,<KEY2:VALUE2>'

  <buffer>
          @type memory
          flush_thread_count 4
          flush_interval 3s
          chunk_limit_size 5m
          chunk_limit_records 500
  </buffer>
</match>
```

By default, the plugin is configured to send logs through HTTPS (port 443) using gzip compression.
You can change this behavior by using the following parameters:

- `use_http`: Set this to `false` if you want to use TCP forwarding and update the `host` and `port` accordingly (default is `true`)
- `use_compression`: Compression is only available for HTTP. Disable it by setting this to `false` (default is `true`)
- `compression_level`: Set the compression level from HTTP. The range is from 1 to 9, 9 being the best ratio (default is `6`)

Additional parameters can be used to change the endpoint used in order to go through a proxy:

- `host`: The proxy endpoint for logs not directly forwarded to Datadog (default value: `http-intake.logs.datadoghq.com`).
- `port`: The proxy port for logs not directly forwarded to Datadog (default value: `80`).
- `ssl_port`: The port used for logs forwarded with a secure TCP/SSL connection to Datadog (default value: `443`).
- `use_ssl`: Instructs the Agent to initialize a secure TCP/SSL connection to Datadog (default value: `true`).
- `no_ssl_validation`: Disables SSL hostname validation (default value: `false`).

**Note**: Set `host` and `port` to your region {{< region-param key="http_endpoint" code="true" >}} {{< region-param key="http_port" code="true" >}}.

```conf
<match datadog.**>

  #...
  host 'http-intake.logs.datadoghq.eu'

</match>
```

###### Kubernetes and Docker tags

Datadog tags are critical to be able to jump from one part of the product to another. Having the right metadata associated with your logs is therefore important in jumping from a container view or any container metrics to the most related logs.

If your logs contain any of the following attributes, these attributes are automatically added as Datadog tags on your logs:

- `kubernetes.container_image`
- `kubernetes.container_name`
- `kubernetes.namespace_name`
- `kubernetes.pod_name`
- `docker.container_id`

While the Datadog Agent collects Docker and Kubernetes metadata automatically, FluentD requires a plugin for this. Datadog recommends using [fluent-plugin-kubernetes_metadata_filter][12] to collect this metadata.

Configuration example:

```conf
# Collect metadata for logs tagged with "kubernetes.**"
 <filter kubernetes.*>
   type kubernetes_metadata
 </filter>
```

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][13] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                             |
| -------------------- | ----------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `fluentd`                                                         |
| `<INIT_CONFIG>`      | blank or `{}`                                                     |
| `<INSTANCE_CONFIG>`  | `{"monitor_agent_url": "http://%%host%%:24220/api/plugins.json"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][14] and look for `fluentd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][15] for a list of metrics provided by this integration.

### Events

The FluentD check does not include any events.

### Service Checks

See [service_checks.json][16] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][17].

## Further Reading

- [How to monitor Fluentd with Datadog][18]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/fluentd/images/snapshot-fluentd.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/fluentd/datadog_checks/fluentd/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://github.com/DataDog/fluent-plugin-datadog
[7]: https://docs.datadoghq.com/logs/processing/#edit-reserved-attributes
[8]: https://docs.datadoghq.com/integrations/#cat-log-collection
[9]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[10]: https://docs.datadoghq.com/getting_started/tagging/assigning_tags/
[11]: https://app.datadoghq.com/infrastructure
[12]: https://github.com/fabric8io/fluent-plugin-kubernetes_metadata_filter
[13]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[15]: https://github.com/DataDog/integrations-core/blob/master/fluentd/metadata.csv
[16]: https://github.com/DataDog/integrations-core/blob/master/fluentd/assets/service_checks.json
[17]: https://docs.datadoghq.com/help/
[18]: https://www.datadoghq.com/blog/monitor-fluentd-datadog
