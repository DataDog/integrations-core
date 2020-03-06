# Agent Integration: Sidekiq

## Overview

This check monitors [Sidekiq][3] through [Dogstatsd][5]. It collects metrics through [Datadog's Dogstatsd Ruby client][4].

**Note** Only Sidekiq Pro or Enterprise users can collect metrics.

## Setup

### Installation

The Sidekiq check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Enable your metrics by including:

```ruby
    require 'datadog/statsd' # gem 'dogstatsd-ruby'

    Sidekiq::Pro.dogstatsd = ->{ Datadog::Statsd.new("metrics.example.com", 8125) }

    Sidekiq.configure_server do |config|
      config.server_middleware do |chain|
        require 'sidekiq/middleware/server/statsd'
        chain.add Sidekiq::Middleware::Server::Statsd
      end
    end
```

    See the Sidekiq [Pro][6] and [Enterprise][7] documentation for more information and [Datadog Ruby][7] documentation for further configuration options.


3. [Restart the Agent][8].

### Validation

[Run the Agent's `status` subcommand][10] and look for `sidekiq` under the Checks section.

## Data Collected

### Metrics

Sidekiq does not include any metrics.

### Log Collection


1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `sidekiq.d/conf.yaml` file to start collecting your Sidekiq logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/Sidekiq.log
          source: sidekiq
          sourcecategory: jobrunner
          service: <SERVICE_NAME>
    ```

     Change the `path` and `service` parameter values and configure them for your environment. If you cannot find your logs, [you can look in the sidekiq documentation to see how to change your logging][9].

3. [Restart the Agent][8].

### Service Checks

Sidekiq does not include any service checks.

### Events

Sidekiq does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://sidekiq.org/
[4]: https://github.com/DataDog/dogstatsd-ruby
[5]: https://docs.datadoghq.com/developers/dogstatsd/
[6]: https://github.com/mperham/sidekiq/wiki/Pro-Metrics
[7]: https://github.com/mperham/sidekiq/wiki/Ent-Historical-Metrics
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://github.com/mperham/sidekiq/wiki/Logging#log-file
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
