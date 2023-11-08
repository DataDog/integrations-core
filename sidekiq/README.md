# Agent Integration: Sidekiq

## Overview

This integration monitors [Sidekiq][1] through [Dogstatsd][2]. It collects metrics through [Datadog's Dogstatsd Ruby client][3].

**Note** Only Sidekiq Pro (>= 3.6) or Enterprise (>= 1.1.0) users can collect metrics.

## Setup

### Installation

The Sidekiq integration is packaged with the [Datadog Agent][4].
No additional installation is needed on your server.

### Configuration

1. Install the `dogstatsd-ruby` [gem][3]:

   ```
    gem install dogstatsd-ruby
   ```

2. Enable Sidekiq Pro metric collection by including this in your initializer; for a containerized deployment, update `localhost` to your Agent container address:

   ```ruby
        require 'datadog/statsd' # gem 'dogstatsd-ruby'

        Sidekiq::Pro.dogstatsd = ->{ Datadog::Statsd.new('localhost', 8125, namespace:'sidekiq') }

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

    See the Sidekiq [Pro][5] and [Enterprise][6] documentation for more information, and the [Dogstatsd Ruby][3] documentation for further configuration options.

3. Update the [Datadog Agent main configuration file][7] `datadog.yaml` by adding the following configs:

   ```yaml
   # dogstatsd_mapper_cache_size: 1000  # default to 1000
   dogstatsd_mapper_profiles:
     - name: sidekiq
       prefix: "sidekiq."
       mappings:
         - match: 'sidekiq\.sidekiq\.(.*)'
           match_type: "regex"
           name: "sidekiq.$1"
         - match: 'sidekiq\.jobs\.(.*)\.perform'
           name: "sidekiq.jobs.perform"
           match_type: "regex"
           tags:
             worker: "$1"
         - match: 'sidekiq\.jobs\.(.*)\.(count|success|failure)'
           name: "sidekiq.jobs.worker.$2"
           match_type: "regex"
           tags:
             worker: "$1"
    ```
    
    These parameters can also be set by adding the `DD_DOGSTATSD_MAPPER_PROFILES` environment variable to the Datadog Agent. 

4. [Restart the Agent][8].

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

The Sidekiq integration also allows custom metrics, see [Sidekiq Enterprise Historical Metrics][10].

### Log collection

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

     Change the `path` and `service` parameter values and configure them for your environment. If you cannot find your logs, see [Sidekiq Logging][11].

3. [Restart the Agent][8].

### Service Checks

Sidekiq does not include any service checks.

### Events

Sidekiq does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][12].

[1]: https://sidekiq.org/
[2]: https://docs.datadoghq.com/developers/dogstatsd/
[3]: https://github.com/DataDog/dogstatsd-ruby
[4]: https://app.datadoghq.com/account/settings/agent/latest
[5]: https://github.com/mperham/sidekiq/wiki/Pro-Metrics
[6]: https://github.com/mperham/sidekiq/wiki/Ent-Historical-Metrics
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://github.com/DataDog/integrations-core/blob/master/sidekiq/metadata.csv
[10]: https://github.com/mperham/sidekiq/wiki/Ent-Historical-Metrics#custom
[11]: https://github.com/mperham/sidekiq/wiki/Logging#log-file
[12]: https://docs.datadoghq.com/help/
