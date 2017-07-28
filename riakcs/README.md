# RiakCS Check

# Overview

Capture RiakCS metrics in Datadog to:

* Visualize key RiakCS metrics.
* Correlate RiakCS performance with the rest of your applications.

# Installation

The RiakCS check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your RiakCS nodes. If you need the newest version of the check, install the `dd-check-riakcs` package.
# Configuration

Create a file `riakcs.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost 
    port: 8080 
    access_id: <YOUR_ACCESS_KEY>
    access_secret: <YOUR_ACCESS_SECRET>
#   is_secure: true # set to false if your endpoint doesn't use SSL
#   s3_root: s3.amazonaws.com # 
```

Restart the Agent to start sending RiakCS metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `riakcs` under the Checks section:

```
  Checks
  ======
    [...]

    riakcs
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

# Compatibility

The riakcs check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/riakcs/metadata.csv) for a list of metrics provided by this check.

# Service Checks

**riakcs.can_connect**:

Returns CRITICAL if the Agent cannot connect to the RiakCS endpoint to collect metrics, otherwise OK.
