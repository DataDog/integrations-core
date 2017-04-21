# Elasticsearch Integration

# Overview

Stay up-to-date on the health of your Elasticsearch cluster, from its overall status down to JVM heap usage and everything in between. Know when you need to revive a replica, add capacity to the cluster, or otherwise tweak its configuration. Watch your cluster metrics respond when you do so.

The Datadog Agent's Elasticsearch check collects metrics for search and indexing performance, memory usage and garbage collection, node availability, shard statistics, disk space and performance, pending tasks, and many more. The Agent also sends events and service checks for the overall status of your cluster.

# Installation

The Elasticsearch check is packaged with the Datadog Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Elasticsearch nodes or on some other server if you use hosted Elasticsearch (e.g. Elastic Cloud). If you need the newest version of the Elasticsearch check, install the `dd-check-elastic` package; this package's check will override the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

# Configuration

Create a file `elastic.yaml` in the Datadog Agent's `conf.d` directory:

```
init_config:

instances:
  - url: http://localhost:9200 # or wherever your cluster API is listening
  - cluster_stats: false # set to true ONLY if you're not running the Elasticsearch check on individual nodes
  - pshard_stats: true   # clusterwise metrics
  - pending_task_stats: true
```

If you're collecting Elasticsearch metrics from just one Datadog Agent running outside the cluster — e.g. if you use Elastic Cloud — set `cluster_stats` to true.

See [the sample elastic.yaml](https://github.com/Datadog/integrations-core/blob/master/elastic/conf.yaml.example) for all available configuration options, including those for authentication and SSL verification.

Restart the Agent to begin sending Elasticsearch metrics to Datadog.

# Validation

Run the Agent's info subcommand and look for elastic under the Checks section:

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

# Troubleshooting

## Agent cannot connect
```
    elastic
    -------
      - instance #0 [ERROR]: "('Connection aborted.', error(111, 'Connection refused'))"
      - Collected 0 metrics, 0 events & 1 service check
```

Check that the `url` in `elastic.yaml` is correct.

# Compatibility

The Elasticsearch check is compatible with all major platforms

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/redisdb/metadata.csv) for a list of metrics provided by this integration.

# Events

The Elasticsearch check emits an event to Datadog each time the overall status of your Elasticsearch cluster changes — red, yellow, or green.

# Service checks

`elasticsearch.cluster_health`:

Return `OK` if the cluster status is green, `Warn` if yellow, and `Critical` otherwise.

`elasticsearch.can_connect`:

Returns `Critical` if the Agent cannot connect to Elasticsearch to collect metrics.

# Further Reading

To get a better idea of how (or why) to integrate your Elasticsearch cluster with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-elasticsearch-performance-metrics/) about it.
