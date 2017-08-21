# Ceph Integration

## Overview

Enable the Datadog-Ceph integration to:

  * Track disk usage across storage pools
  * Receive service checks in case of issues
  * Monitor I/O performance metrics

## Setup
### Installation

The Ceph check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Ceph servers.

### Configuration

Create a file `ceph.yaml` in the Agent's `conf.d` directory:

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

Run the Agent's `info` subcommand and look for `ceph` under the Checks section:

```
  Checks
  ======
    [...]

    ceph
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/ceph/metadata.csv) for a list of metrics provided by this integration.

### Events
The Ceph check does not include any event at this time.

### Service Checks
The Ceph check does not include any service check at this time.

## Troubleshooting

## Further Reading
### Blog Article
To get a better idea of how (or why) to integrate your Ceph cluster with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitor-ceph-datadog/) about it.
