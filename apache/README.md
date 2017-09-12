# Agent Check: Apache Web Server

## Overview

The Apache check tracks requests per second, bytes served, number of worker threads, service uptime, and more.

## Setup
### Installation

The Apache check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Apache servers.

Install `mod_status` on your Apache servers and enable `ExtendedStatus`.

### Configuration

Create a file `apache.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - apache_status_url: http://example.com/server-status?auto
#   apache_user: example_user # if apache_status_url needs HTTP basic auth
#   apache_password: example_password
#   disable_ssl_validation: true # if you need to disable SSL cert validation, i.e. for self-signed certs
```

Restart the Agent to start sending Apache metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `apache` under the Checks section:

```
  Checks
  ======
    [...]

    apache
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Apache check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/apache/metadata.csv) for a list of metrics provided by this check.

### Events
The Apache check does not include any event at this time.

### Service Checks

**apache.can_connect**:

Returns CRITICAL if the Agent cannot connect to the configured `apache_status_url`, otherwise OK.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/agent_metrics/metadata.csv) for a list of metrics provided by this integration.

### Events
The Agent_metrics check does not include any event at this time.

### Service Checks
The Agent_metrics check does not include any service check at this time.

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
To get a better idea of how (or why) to integrate your Apache web server with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitoring-apache-web-server-performance/).
