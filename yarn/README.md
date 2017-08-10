# Agent Check: Hadoop YARN

## Overview

This check collects metrics from your YARN ResourceManager, including:

* Cluster-wide metrics: number of running apps, running containers, unhealthy nodes, etc
* Per-application metrics: app progress, elapsed running time, running containers, memory use, etc
* Node metrics: available vCores, time of last health update, etc

And more.

## Installation

The YARN check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your YARN ResourceManager. If you need the newest version of the check, install the `dd-check-yarn` package.

## Configuration

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

## Validation

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

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/yarn/metadata.csv) for a list of metrics provided by this check.

## Service Checks

**yarn.can_connect**:

Returns CRITICAL if the Agent cannot connect to the ResourceManager URI to collect metrics, otherwise OK.

## Further Reading

To get a better idea of how (or why) to monitor a hadoop architecture with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/hadoop-architecture-overview/) about it.
