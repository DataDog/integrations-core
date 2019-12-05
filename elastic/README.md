# Elasticsearch Integration

![Elasitc search dashboard][1]

## Overview

Stay up-to-date on the health of your Elasticsearch cluster, from its overall status down to JVM heap usage and everything in between. Get notified when you need to revive a replica, add capacity to the cluster, or otherwise tweak its configuration. After doing so, track how your cluster metrics respond.

The Datadog Agent's Elasticsearch check collects metrics for search and indexing performance, memory usage and garbage collection, node availability, shard statistics, disk space and performance, pending tasks, and many more. The Agent also sends events and service checks for the overall status of your cluster.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Elasticsearch check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Elasticsearch nodes, or on some other server if you use a hosted Elasticsearch (e.g. Elastic Cloud).

### Configuration

1. Edit the `elastic.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your Elasticsearch [metrics](#metric-collection) and [logs](#log-collection).
  See the [sample elastic.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6]

#### Metric collection

*  Add this configuration block to your `elastic.yaml` file to start gathering your [ElasticSearch metrics](#metrics):

```yaml
init_config:

instances:
  - url: http://localhost:9200 # or wherever your cluster API is listening
    cluster_stats: false # set true ONLY if you're not running the check on each cluster node
    pshard_stats: true # the agent sends primary shard metrics
    index_stats: true # the agent sends index level metrics
    pending_task_stats: true # the agent sends cluster-wide pending task metrics
```

**Note**:

* If you're collecting Elasticsearch metrics from just one Datadog Agent running outside the cluster - e.g. if you use a hosted Elasticsearch - set `cluster_stats` to true.

* To use the Agent's Elasticsearch integration for the AWS Elasticsearch services, set the `url` parameter to point to your AWS Elasticsearch stats URL.

See the [sample elastic.yaml][5] for all available configuration options, including those for authentication to and SSL verification of your cluster's API `url`.

Finally, [Restart the Agent][6] to begin sending Elasticsearch metrics to Datadog.

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `elastic.d/conf.yaml` file to start collecting your Elasticsearch logs:

    ```yaml
      logs:
          - type: file
            path: /var/log/elasticsearch/*.log
            source: elasticsearch
            service: myservice
    ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][8] and look for `elastic` under the Checks section.

## Data Collected

By default, not all of the following metrics are sent by the Agent. To send all metrics, configure flags in `elastic.yaml` as shown above.

* `pshard_stats` sends **elasticsearch.primaries.\*** and **elasticsearch.indices.count** metrics
* `index_stats` sends **elasticsearch.index.\*** metrics
* `pending_task_stats` sends **elasticsearch.pending_\*** metrics

For version >=6.3.0, set `xpack.monitoring.collection.enabled` configuration to `true` in your Elasticsearch configuration in order to collect all `elasticsearch.thread_pool.write.*` metrics. See [Elasticsearch release notes - monitoring section][9].

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Events

The Elasticsearch check emits an event to Datadog each time the overall status of your Elasticsearch cluster changes - red, yellow, or green.

### Service checks

`elasticsearch.cluster_health`:

Returns `OK` if the cluster status is green, `Warn` if yellow, and `Critical` otherwise.

`elasticsearch.can_connect`:

Returns `Critical` if the Agent cannot connect to Elasticsearch to collect metrics.

## Troubleshooting

* [Agent can't connect][11]
* [Why isn't Elasticsearch sending all my metrics?][12]

## Further Reading
To get a better idea of how (or why) to integrate your Elasticsearch cluster with Datadog, check out our [series of blog posts][13] about it.


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/elastic/images/elasticsearch-dash.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/elastic/datadog_checks/elastic/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://www.elastic.co/guide/en/elasticsearch/reference/6.3/release-notes-6.3.0.html
[10]: https://github.com/DataDog/integrations-core/blob/master/elastic/metadata.csv
[11]: https://docs.datadoghq.com/integrations/faq/elastic-agent-can-t-connect
[12]: https://docs.datadoghq.com/integrations/faq/why-isn-t-elasticsearch-sending-all-my-metrics
[13]: https://www.datadoghq.com/blog/monitor-elasticsearch-performance-metrics
