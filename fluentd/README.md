# Fluentd Integration

![Fluentd Dashboard][1]

## Overview

Get metrics from Fluentd to:

* Visualize Fluentd performance.
* Correlate the performance of Fluentd with the rest of your applications.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Fluentd check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Fluentd servers.

### Configuration

Edit the `fluentd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your FluentD [metrics](#metric-collection) and [logs](#log-collection).
See the [sample fluentd.d/conf.yaml][5] for all available configuration options.

#### Prepare Fluentd

In your fluentd configuration file, add a `monitor_agent` source:

```
<source>
  @type monitor_agent
  bind 0.0.0.0
  port 24220
</source>
```

#### Metric Collection

1. Add this configuration block to your `fluentd.d/conf.yaml` file to start gathering your [Fluentd metrics](#metrics):

    ```yaml
      init_config:

      instances:
        - monitor_agent_url: http://localhost:24220/api/plugins.json
          #tag_by: "type" # defaults to 'plugin_id'
          #plugin_ids:    # collect metrics only on your chosen plugin_ids (optional)
          #  - plg1
          #  - plg2
    ```

    See the [sample fluentd.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6] to begin sending Fluentd metrics to Datadog.

#### Log Collection

You can use the [Datadog FluentD plugin][7] to forward the logs directly from FluentD to your Datadog account.

##### Add metadata to your logs

Proper metadata (including hostname and source) is the key to unlocking the full potential of your logs in Datadog. By default, the hostname and timestamp fields should be properly remapped via the [remapping for reserved attributes][8].

##### Source and Custom tags

Add the `ddsource` attribute with [the name of the log integration][9] in your logs in order to trigger the [integration automatic setup][10] in Datadog.
[Host tags][11] are automatically set on your logs if there is a matching hostname in your [infrastructure list][12]. Use the `ddtags` attribute to add custom tags to your logs:

Setup Example:

```
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
  dd_sourcecategory '<SOURCE_CATEGORY>'

</match>
```

Additional parameters can be used to change the endpoint used in order to go through a proxy:

* `host`: Proxy endpoint when logs are not directly forwarded to Datadog (default value is `intake.logs.datadoghq.com`)
* `port`: Proxy port when logs are not directly forwarded to Datadog (default value is `10514`)
* `ssl_port`: Port used when logs are forwarded in a secure TCP/SSL connection to Datadog (default is `10516`)
* `use_ssl`: If `true`, the Agent initializes a secure TCP/SSL connection to Datadog. (default value is `true`)

This also can be used to send logs to **Datadog EU** by setting:

```
<match datadog.**>

  ...
  host 'tcp-intake.logs.datadoghq.eu'
  ssl_port '443'

</match>
```

##### Kubernetes and Docker tags

Datadog tags are critical to be able to jump from one part of the product to another. Having the right metadata associated with your logs is therefore important in jumping from a container view or any container metrics to the most related logs.

If your logs contain any of the following attributes, these attributes are automatically added as Datadog tags on your logs:

* `kubernetes.container_image`
* `kubernetes.container_name`
* `kubernetes.namespace_name`
* `kubernetes.pod_name`
* `docker.container_id`

While the Datadog Agent collects Docker and Kubernetes metadata automatically, FluentD requires a plugin for this. We recommend using [fluent-plugin-kubernetes_metadata_filter][13] to collect this metadata.

Configuration example:

```
# Collect metadata for logs tagged with "kubernetes.**"
 <filter kubernetes.*>
   type kubernetes_metadata
 </filter>
```


### Validation

[Run the Agent's `status` subcommand][14] and look for `fluentd` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][15] for a list of metrics provided by this integration.

### Events
The FluentD check does not include any events.

### Service Checks

`fluentd.is_ok`:

Returns 'Critical' if the Agent cannot connect to Fluentd to collect metrics. This is the check which most other integrations would call `can_connect`.

## Troubleshooting
Need help? Contact [Datadog support][16].

## Further Reading

* [How to monitor Fluentd with Datadog][17]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/fluentd/images/snapshot-fluentd.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/fluentd/datadog_checks/fluentd/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: http://www.rubydoc.info/gems/fluent-plugin-datadog
[8]: https://docs.datadoghq.com/logs/processing/#edit-reserved-attributes
[9]: https://docs.datadoghq.com/integrations/#cat-log-collection
[10]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[11]: https://docs.datadoghq.com/getting_started/tagging/assigning_tags
[12]: https://app.datadoghq.com/infrastructure
[13]: https://github.com/fabric8io/fluent-plugin-kubernetes_metadata_filter
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[15]: https://github.com/DataDog/integrations-core/blob/master/fluentd/metadata.csv
[16]: https://docs.datadoghq.com/help
[17]: https://www.datadoghq.com/blog/monitor-fluentd-datadog
