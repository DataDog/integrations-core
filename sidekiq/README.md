# Agent Integration: Sidekiq

## Overview

This integration monitors [Sidekiq][3] through [Dogstatsd][5]. It collects metrics through [Datadog's Dogstatsd Ruby client][4].

**Note** Only Sidekiq Pro (>= 3.6) or Enterprise (>= 1.1.0) users can collect metrics.

## Setup

### Installation

The Sidekiq integration is packaged with the [Datadog Agent][2].
No additional installation is needed on your server.

### Configuration

1. Install the `dogstatsd-ruby` [gem][4]:

   ```
    gem install dogstatsd-ruby
   ```

2. Enable Sidekiq Pro metric collection by including this in your initializer:

   ```ruby
        require 'datadog/statsd' # gem 'dogstatsd-ruby'

        Sidekiq::Pro.dogstatsd = ->{ Datadog::Statsd.new('metrics.example.com', 8125, namespace:'sidekiq') }

        Sidekiq.configure_server do |config|
          config.server_middleware do |chain|
            require 'sidekiq/middleware/server/statsd'
            chain.add Sidekiq::Middleware::Server::Statsd
          end
        end
   ```

    If you are using Sidekiq Enterprise and would like to collect historical metrics, include this line as well:

   ```ruby
          Sidekiq.configure_server do |config|
            # history is captured every 30 seconds by default
            config.retain_history(30)
          end
   ```

    See the Sidekiq [Pro][6] and [Enterprise][7] documentation for more information, and the [Datadog Ruby][7] documentation for further configuration options.

3. Update the [Datadog Agent main configuration file][13] `datadog.yaml` by adding the following configs:

   ```yaml
   # dogstatsd_mapper_cache_size: 1000  # default to 1000
   dogstatsd_mapper_profiles:
     - name: sidekiq
       prefix: "sidekiq."
       mappings:
         - match: "sidekiq.sidekiq.*"
           name: "sidekiq.*"
         - match: "sidekiq.jobs.*.perform.avg"
           name: "sidekiq.jobs.perform.avg"
           tags:
             worker: "$1"
         - match: "sidekiq.jobs.*.perform.count"
           name: "sidekiq.jobs.perform.count"
           tags:
             worker: "$1"
         - match: "sidekiq.jobs.*.perform.max"
           name: "sidekiq.jobs.perform.max"
           tags:
             worker: "$1"
         - match: "sidekiq.jobs.*.perform.median"
           name: "sidekiq.jobs.perform.median"
           tags:
             worker: "$1"
         - match: "sidekiq.jobs.*.perform.95percentile"
           name: "sidekiq.jobs.perform.95percentile"
           tags:
             worker: "$1"

    ```

4. [Restart the Agent][8].

### Validation

[Run the Agent's `status` subcommand][10] and look for `sidekiq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][12] for a list of metrics provided by this integration.

The Sidekiq integration also allows custom metrics, see the [Sidekiq documentation][11] for custom metric inspiration.

### Log Collection


1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `sidekiq.d/conf.yaml` file to start collecting your Sidekiq logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/sidekiq.log
          source: sidekiq
          service: <SERVICE>
    ```

     Change the `path` and `service` parameter values and configure them for your environment. If you cannot find your logs, [see the Sidekiq documentation on more details about logs][9].

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
[11]: https://github.com/mperham/sidekiq/wiki/Ent-Historical-Metrics#custom
[12]: https://github.com/DataDog/integrations-core/blob/master/sidekiq/metadata.csv
[13]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
