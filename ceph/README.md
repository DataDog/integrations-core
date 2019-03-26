# Ceph Integration

![Ceph dashboard][1]

## Overview

Enable the Datadog-Ceph integration to:

  * Track disk usage across storage pools
  * Receive service checks in case of issues
  * Monitor I/O performance metrics

## Setup
### Installation

The Ceph check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Ceph servers.

### Configuration

Edit the file `ceph.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
See the [sample ceph.d/conf.yaml][4] for all available configuration options:

```yaml
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

[Run the Agent's `status` subcommand][5] and look for `ceph` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

Note: If you are running ceph luminous or later, you will not see the metric `ceph.osd.pct_used`.

### Events
The Ceph check does not include any events.

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
Need help? Contact [Datadog support][7].

## Further Reading

* [Monitor Ceph: From node status to cluster-wide performance][8]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/ceph/images/ceph_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/ceph/datadog_checks/ceph/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/ceph/metadata.csv
[7]: https://docs.datadoghq.com/help
[8]: https://www.datadoghq.com/blog/monitor-ceph-datadog
