# Etcd Integration

# Overview

Collect etcd metrics to:

* Monitor the health of your etcd cluster.
* Know when host configurations may be out of sync.
* Correlate the performance of etcd with the rest of your applications.

# Installation

The etcd check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your etcd instance(s).

# Configuration

Create a file `etcd.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - url: "https://server:port" # API endpoint of your etcd instance
```

Restart the Agent to begin sending etcd metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `etcd` under the Checks section:

```
  Checks
  ======
    [...]

    etcd
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 0 service checks

    [...]
```

# Troubleshooting

# Compatibility

The etcd check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/etcd/metadata.csv) for a list of metrics provided by this integration.

# Events

# Service Checks

`etcd.can_connect`:

Returns 'Critical' if the Agent cannot collect metrics from your etcd API endpoint.

# Further Reading

To get a better idea of how (or why) to integrate etcd with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitor-etcd-performance/) about it.
