# Elasticsearch Integration

![Elasitc search dashboard][1]

## Overview

Stay up-to-date on the health of your Elasticsearch cluster, from its overall status down to JVM heap usage and everything in between. Get notified when you need to revive a replica, add capacity to the cluster, or otherwise tweak its configuration. After doing so, track how your cluster metrics respond.

The Datadog Agent's Elasticsearch check collects metrics for search and indexing performance, memory usage and garbage collection, node availability, shard statistics, disk space and performance, pending tasks, and many more. The Agent also sends events and service checks for the overall status of your cluster.

## Setup

### Installation

The Elasticsearch check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Elasticsearch nodes, or on some other server if you use a hosted Elasticsearch (e.g. Elastic Cloud).

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `elastic.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Elasticsearch [metrics](#metrics). See the [sample elastic.d/conf.yaml][4] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param url - string - required
     ## The URL where Elasticsearch accepts HTTP requests. This is used to
     ## fetch statistics from the nodes and information about the cluster health.
     #
     - url: http://localhost:9200
   ```

    **Notes**:

      - If you're collecting Elasticsearch metrics from just one Datadog Agent running outside the cluster - e.g. if you use a hosted Elasticsearch - set `cluster_stats` to true.
      - To use the Agent's Elasticsearch integration for the AWS Elasticsearch services, set the `url` parameter to point to your AWS Elasticsearch stats URL.

2. [Restart the Agent][5].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in the `datadog.yaml` file with:

   ```yaml
   logs_enabled: true
   ```

2. To collect search slow logs and index slow logs, [configure your Elasticsearch settings][14]. By default, slow logs are not enabled.

   - To configure index slow logs for a given index `<INDEX>`:

     ```shell
     curl -X PUT "localhost:9200/<INDEX>/_settings?pretty" -H 'Content-Type: application/json' -d' {
       "index.indexing.slowlog.threshold.index.warn": "0ms",
       "index.indexing.slowlog.threshold.index.info": "0ms",
       "index.indexing.slowlog.threshold.index.debug": "0ms",
       "index.indexing.slowlog.threshold.index.trace": "0ms",
       "index.indexing.slowlog.level": "trace",
       "index.indexing.slowlog.source": "1000"
     }
     ```

   - To configure search slow logs for a given index `<INDEX>`:

     ```shell
     curl -X PUT "localhost:9200/<INDEX>/_settings?pretty" -H 'Content-Type: application/json' -d' {
       "index.search.slowlog.threshold.query.warn": "0ms",
       "index.search.slowlog.threshold.query.info": "0ms",
       "index.search.slowlog.threshold.query.debug": "0ms",
       "index.search.slowlog.threshold.query.trace": "0ms",
       "index.search.slowlog.threshold.fetch.warn": "0ms",
       "index.search.slowlog.threshold.fetch.info": "0ms",
       "index.search.slowlog.threshold.fetch.debug": "0ms",
       "index.search.slowlog.threshold.fetch.trace": "0ms"
     }
     ```

3. Add this configuration block to your `elastic.d/conf.yaml` file to start collecting your Elasticsearch logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/elasticsearch/*.log
       source: elasticsearch
       service: "<SERVICE_NAME>"
   ```

   - Add additional instances to start collecting slow logs:

     ```yaml
     - type: file
       path: "/var/log/elasticsearch/\
             <CLUSTER_NAME>_index_indexing_slowlog.log"
       source: elasticsearch
       service: "<SERVICE_NAME>"

     - type: file
       path: "/var/log/elasticsearch/\
             <CLUSTER_NAME>_index_search_slowlog.log"
       source: elasticsearch
       service: "<SERVICE_NAME>"
     ```

     Change the `path` and `service` parameter values and configure them for your environment.

4. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                              |
| -------------------- | ---------------------------------- |
| `<INTEGRATION_NAME>` | `elastic`                          |
| `<INIT_CONFIG>`      | blank or `{}`                      |
| `<INSTANCE_CONFIG>`  | `{"url": "https://%%host%%:9200"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][7].

| Parameter      | Value                                                      |
| -------------- | ---------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "elasticsearch", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][8] and look for `elastic` under the Checks section.

## Data Collected

By default, not all of the following metrics are sent by the Agent. To send all metrics, configure flags in `elastic.yaml` as shown above.

- `pshard_stats` sends **elasticsearch.primaries.\*** and **elasticsearch.indices.count** metrics
- `index_stats` sends **elasticsearch.index.\*** metrics
- `pending_task_stats` sends **elasticsearch.pending\_\*** metrics

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

- [Agent can't connect][11]
- [Why isn't Elasticsearch sending all my metrics?][12]

## Further Reading

To get a better idea of how (or why) to integrate your Elasticsearch cluster with Datadog, check out our [series of blog posts][13] about it.

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/elastic/images/elasticsearch-dash.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/elastic/datadog_checks/elastic/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[7]: https://docs.datadoghq.com/agent/docker/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://www.elastic.co/guide/en/elasticsearch/reference/6.3/release-notes-6.3.0.html
[10]: https://github.com/DataDog/integrations-core/blob/master/elastic/metadata.csv
[11]: https://docs.datadoghq.com/integrations/faq/elastic-agent-can-t-connect
[12]: https://docs.datadoghq.com/integrations/faq/why-isn-t-elasticsearch-sending-all-my-metrics
[13]: https://www.datadoghq.com/blog/monitor-elasticsearch-performance-metrics
[14]: https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-slowlog.html
