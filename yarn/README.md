# Agent Check: Hadoop YARN

## Overview

This check collects metrics from your YARN ResourceManager, including:

* Cluster-wide metrics: number of running apps, running containers, unhealthy nodes, etc
* Per-application metrics: app progress, elapsed running time, running containers, memory use, etc
* Node metrics: available vCores, time of last health update, etc

And more.
## Setup
### Installation

The YARN check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your YARN ResourceManager. If you need the newest version of the check, install the `dd-check-yarn` package.

### Configuration

Create a file `yarn.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - resourcemanager_uri: http://localhost:8088 # or whatever your resource manager listens
    cluster_name: MyCluster # used to tag metrics, i.e. 'cluster_name:MyCluster'; default is 'default_cluster'
    collect_app_metrics: true
```

See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/yarn/conf.yaml.example) for a comprehensive list and description of all check options.

Restart the Agent to start sending YARN metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `yarn` under the Checks section:

```
  Checks
  ======
    [...]

    yarn
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The yarn check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/yarn/metadata.csv) for a list of metrics provided by this check.

### Events
The Yarn check does not include any event at this time.

### Service Checks
**yarn.can_connect**:

Returns CRITICAL if the Agent cannot connect to the ResourceManager URI to collect metrics, otherwise OK.

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
To get a better idea of how (or why) to monitor a hadoop architecture with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/hadoop-architecture-overview/) about it.
