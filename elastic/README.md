# Elasticsearch Integration
{{< img src="integrations/elasticsearch/elasticsearchgraph.png" alt="Elasticsearch" responsive="true" popup="true">}}

## Overview

Stay up-to-date on the health of your Elasticsearch cluster, from its overall status down to JVM heap usage and everything in between. Get notified when you need to revive a replica, add capacity to the cluster, or otherwise tweak its configuration. After doing so, track how your cluster metrics respond.

The Datadog Agent's Elasticsearch check collects metrics for search and indexing performance, memory usage and garbage collection, node availability, shard statistics, disk space and performance, pending tasks, and many more. The Agent also sends events and service checks for the overall status of your cluster.

## Setup
### Installation

The Elasticsearch check is packaged with the Datadog Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Elasticsearch nodes, or on some other server if you use a hosted Elasticsearch (e.g. Elastic Cloud).

If you need the newest version of the Elasticsearch check, install the `dd-check-elastic` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

### Configuration

Create a file `elastic.yaml` in the Datadog Agent's `conf.d` directory. See the [sample elastic.yaml](https://github.com/DataDog/integrations-core/blob/master/elastic/conf.yaml.example) for all available configuration options:

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

* To use the Agent's ElasticSearch integration for the Amazon Elasticsearch service, set the `url` parameter on a remote host to point to wherever your AWS elasticsearch stats url is.

See the [sample elastic.yaml](https://github.com/Datadog/integrations-core/blob/master/elastic/conf.yaml.example) for all available configuration options, including those for authentication to and SSL verification of your cluster's API `url`.

Finally, [restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to begin sending Elasticsearch metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `elastic` under the Checks section:

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
