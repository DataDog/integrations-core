# Elasticsearch Integration
{{< img src="integrations/elasticsearch/elasticsearchgraph.png" alt="Elasticsearch" responsive="true" popup="true">}}

## Overview

Stay up-to-date on the health of your Elasticsearch cluster, from its overall status down to JVM heap usage and everything in between. Get notified when you need to revive a replica, add capacity to the cluster, or otherwise tweak its configuration. After doing so, track how your cluster metrics respond.

The Datadog Agent's Elasticsearch check collects metrics for search and indexing performance, memory usage and garbage collection, node availability, shard statistics, disk space and performance, pending tasks, and many more. The Agent also sends events and service checks for the overall status of your cluster.

## Setup
### Installation

The Elasticsearch check is packaged with the Datadog Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Elasticsearch nodes, or on some other server if you use a hosted Elasticsearch (e.g. Elastic Cloud).

### Configuration

Create a file `elastic.yaml` in the Datadog Agent's `conf.d` directory. 

#### Metric Collection

*  Add this configuration setup to your `elastic.yaml` file to start gathering your [ElasticSearch metrics](#metrics):

```
init_config:

instances:
  - url: http://localhost:9200 # or wherever your cluster API is listening
    cluster_stats: false # set true ONLY if you're not running the check on each cluster node
    pshard_stats: true
    pending_task_stats: true
```

**Note**:

* If you're collecting Elasticsearch metrics from just one Datadog Agent running outside the cluster — e.g. if you use a hosted Elasticsearch — set `cluster_stats` to true.

* To use the Agent's Elasticsearch integration for the AWS Elasticsearch services, set the `url` parameter to point to your AWS Elasticsearch stats URL.

See the [sample elastic.yaml](https://github.com/Datadog/integrations-core/blob/master/elastic/conf.yaml.example) for all available configuration options, including those for authentication to and SSL verification of your cluster's API `url`.

Finally, [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending Elasticsearch metrics to Datadog.

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, enable it in the `datadog.yaml` file with:

  ```
  logs_enabled: true
  ```

* Then add this configuration setup to your `apache.yaml` file to start collecting your Elasticsearch Logs:

  ```
    logs:
        - type: file
          path: /var/log/elasticsearch/*.log
          source: elasticsearch
          service: myservice
  ```

  Change the `path` and `service` parameter values and configure them for your environment.
  
  * [Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending Elasticsearch logs to Datadog.
  
  **Learn more about log collection [on the log documentation](https://docs.datadoghq.com/logs)**
  
### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `elastic` under the Checks section:

```
  Checks
  ======
    [...]

    elastic
    -------
      - instance #0 [OK]
      - Collected 118 metrics, 0 events & 2 service checks

    [...]
```

## Compatibility

The Elasticsearch check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/elastic/metadata.csv) for a list of metrics provided by this integration.

### Events

The Elasticsearch check emits an event to Datadog each time the overall status of your Elasticsearch cluster changes — red, yellow, or green.

### Service checks

`elasticsearch.cluster_health`:

Returns `OK` if the cluster status is green, `Warn` if yellow, and `Critical` otherwise.

`elasticsearch.can_connect`:

Returns `Critical` if the Agent cannot connect to Elasticsearch to collect metrics.

## Troubleshooting

* [Agent can't connect](https://docs.datadoghq.com/integrations/faq/elastic-agent-can-t-connect)
* [Why isn't Elasticsearch sending all my metrics?](/integrations/faq/why-isn-t-elasticsearch-sending-all-my-metrics)

## Further Reading
To get a better idea of how (or why) to integrate your Elasticsearch cluster with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-elasticsearch-performance-metrics/) about it.
