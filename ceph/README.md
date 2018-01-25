# Ceph Integration
{{< img src="integrations/ceph/ceph_graph.png" alt="Ceph Graph" responsive="true" popup="true">}}
## Overview

Enable the Datadog-Ceph integration to:

  * Track disk usage across storage pools
  * Receive service checks in case of issues
  * Monitor I/O performance metrics

## Setup
### Installation

The Ceph check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Ceph servers.  

If you need the newest version of the Ceph check, install the `dd-check-ceph` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

### Configuration

Create a file `ceph.yaml` in the Agent's `conf.d` directory. See the [sample ceph.yaml](https://github.com/DataDog/integrations-core/blob/master/ceph/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - ceph_cmd: /path/to/your/ceph # default is /usr/bin/ceph
    use_sudo: true               # only if the ceph binary needs sudo on your nodes
```

If you enabled `use_sudo`, add a line like the following to your `sudoers` file:

```
dd-agent ALL=(ALL) NOPASSWD:/path/to/your/ceph
```

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `ceph` under the Checks section:

```
  Checks
  ======
    [...]

   ceph (5.19.0)
   -------------
   - instance #0 [OK]
   - Collected 24 metrics, 0 events & 1 service check

    [...]
```

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/ceph/metadata.csv) for a list of metrics provided by this integration.

Note: If you are running ceph luminous or later, you will not see the metric `ceph.osd.pct_used`.

### Events
The Ceph check does not include any event at this time.

### Service Checks

* `ceph.overall_status` : The Datadog Agent submits a service check for each of Ceph's host health checks.

In addition to this service check, the Ceph check also collects a configurable list of health checks for Ceph luminous and later. By default, these are:

* `ceph.osd_down` : Returns `OK` if your OSDs are all up. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.osd_orphan` : Returns `OK` if you have no orphan OSD. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.osd_full` : Returns `OK` if your OSDs are not full. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.osd_nearfull` : Returns `OK` if your OSDs are not near full. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.pool_full` : Returns `OK` if your pools have not reached their quota. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.pool_near_full` : Returns `OK` if your pools are not near reaching their quota. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.pg_availability` : Returns `OK` if there is full data availability. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.pg_degraded` : Returns `OK` if there is full data redundancy. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.pg_degraded_full` : Returns `OK` if there is enough space in the cluster for data redundancy. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.pg_damaged` : Returns `OK` if there are no inconsistencies after data scrubing. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.pg_not_scrubbed` : Returns `OK` if the PGs were scrubbed recently. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.pg_not_deep_scrubbed` : Returns `OK` if the PGs were deep scrubbed recently. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.cache_pool_near_full` : Returns `OK` if the cache pools are not near full. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.too_few_pgs` : Returns `OK` if the number of PGs is above the min threshold. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.too_many_pgs` : Returns `OK` if the number of PGs is below the max threshold. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.object_unfound` : Returns `OK` if all objects can be found. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.request_slow` : Returns `OK` requests are taking a normal time to process. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

* `ceph.request_stuck` : Returns `OK` requests are taking a normal time to process. Otherwise, returns `WARNING` if the severity is `HEALTH_WARN`, else `CRITICAL`.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitor Ceph: From node status to cluster-wide performance](https://www.datadoghq.com/blog/monitor-ceph-datadog/)
