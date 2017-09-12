# Solr Check

## Overview

The Solr check tracks the state and performance of a Solr cluster. It collects metrics like number of documents indexed, cache hits and evictions, average request times, average requests per second, and more.

## Setup
### Installation

The Solr check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Solr nodes.

This check is JMX-based, so you'll need to enable JMX Remote on your Tomcat servers. Read the [JMX Check documentation](http://docs.datadoghq.com/integrations/java/) for more information on that.

### Configuration

Create a file `solr.yaml` in the Agent's `conf.d` directory:

```
instances:
# location of tomcat
  - host: localhost
    port: 9999

# if tomcat requires authentication
#   user: <TOMCAT_USERNAME>
#   password: <TOMCAT_PASSWORD>

init_config:
  conf:
    - include:
      type: searcher
      attribute:
        maxDoc:
          alias: solr.searcher.maxdoc
          metric_type: gauge
        numDocs:
          alias: solr.searcher.numdocs
          metric_type: gauge
        warmupTime:
          alias: solr.searcher.warmup
          metric_type: gauge
    - include:
      id: org.apache.solr.search.FastLRUCache
      attribute:
        cumulative_lookups:
          alias: solr.cache.lookups
          metric_type: counter
        cumulative_hits:
          alias: solr.cache.hits
          metric_type: counter
        cumulative_inserts:
          alias: solr.cache.inserts
          metric_type: counter
        cumulative_evictions:
          alias: solr.cache.evictions
          metric_type: counter
    - include:
      id: org.apache.solr.search.LRUCache
      attribute:
        cumulative_lookups:
          alias: solr.cache.lookups
          metric_type: counter
        cumulative_hits:
          alias: solr.cache.hits
          metric_type: counter
        cumulative_inserts:
          alias: solr.cache.inserts
          metric_type: counter
        cumulative_evictions:
          alias: solr.cache.evictions
          metric_type: counter
    - include:
      id: org.apache.solr.handler.component.SearchHandler
      attribute:
        errors:
          alias: solr.search_handler.errors
          metric_type: counter
        requests:
          alias: solr.search_handler.requests
          metric_type: counter
        timeouts:
          alias: solr.search_handler.timeouts
          metric_type: counter
        totalTime:
          alias: solr.search_handler.time
          metric_type: counter
        avgTimePerRequest:
          alias: solr.search_handler.avg_time_per_req
          metric_type: gauge
        avgRequestsPerSecond:
          alias: solr.search_handler.avg_requests_per_sec
          metric_type: gauge
```

Again, see the [JMX Check documentation](http://docs.datadoghq.com/integrations/java/) for a list of configuration options usable by all JMX-based checks. The page also describes how the Agent tags JMX metrics.

Restart the Agent to start sending Solr metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `solr` under the Checks section:

```
  Checks
  ======
    [...]

    solr
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The solr check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/solr/metadata.csv) for a list of metrics provided by this check.

### Events
The Solr check does not include any event at this time.

### Service Checks
The Solr check does not include any service check at this time.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)