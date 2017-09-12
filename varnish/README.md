# Agent Check: Varnish

## Overview

This check collects varnish metrics regarding:

* Clients: connections and requests
* Cache performance: hits, evictions, etc
* Threads: creation, failures, threads queued
* Backends: successful, failed, retried connections

It also submits service checks for the health of each backend.

## Setup
### Installation

The varnish check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your varnish servers. If you need the newest version of the check, install the `dd-check-varnish` package.

### Configuration

If you're running Varnish 4.1+, add the dd-agent system user to the varnish group (e.g. `sudo usermod -G varnish -a dd-agent`).

Then, create a file `varnish.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - varnishstat: /usr/bin/varnishstat        # or wherever varnishstat lives
    varnishadm: <PATH_TO_VARNISHADM_BIN>     # to submit service checks for the health of each backend
#   secretfile: <PATH_TO_VARNISH_SECRETFILE> # if you configured varnishadm and your secret file isn't /etc/varnish/secret
#   tags:
#     - instance:production
```

If you don't set `varnishadm`, the Agent won't check backend health. If you do set it, the Agent needs privileges to execute the binary with root privileges. Add the following to your `/etc/sudoers` file:

```
dd-agent ALL=(ALL) NOPASSWD:/usr/bin/varnishadm
```

Restart the Agent to start sending varnish metrics and service checks to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `varnish` under the Checks section:

```
  Checks
  ======
    [...]

    varnish
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```
## Compatibility

The Varnish check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/varnish/metadata.csv) for a list of metrics provided by this check.

### Events
The Varnish check does not include any event at this time.

### Service Checks
**varnish.backend_healthy**:

The Agent submits this service check if you configure `varnishadm`. It submits a service check for each varnish backend, tagging each with `backend:<backend_name>`.

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
See our [series of blog posts](https://www.datadoghq.com/blog/top-varnish-performance-metrics/) about monitoring varnish with Datadog.
