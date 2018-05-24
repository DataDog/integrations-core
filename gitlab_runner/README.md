# Gitlab Runner Integration

## Overview

Integration that allows to:

* Visualize and monitor metrics collected via Gitlab Runners through Prometheus
* Validate that the Gitlab Runner can connect to Gitlab

See https://docs.gitlab.com/runner/monitoring/README.html for
more information about Gitlab Runner and its integration with Prometheus

## Setup
### Installation

The Gitlab Runner check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Gitlab servers.

### Configuration

Edit the `gitlab_runner.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory, to point to the Runner's Prometheus metrics endpoint and to the Gitlab master to have a service check.  
See the [sample gitlab_runner.d/conf.yaml][2] for all available configuration options.

**Note**: The `allowed_metrics` item in the `init_config` section allows to specify the metrics that should be extracted.

**Remarks**: Some metrics should be reported as `rate` (i.e., `ci_runner_errors`)

### Validation

[Run the Agent's `status` subcommand][3] and look for `gitlab_runner` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The Gitlab Runner check does not include any event at this time.

### Service Checks
The Gitlab Runner check currently provides a service check to ensure that the Runner can talk to the Gitlab master and another one to ensure that the
local Prometheus endpoint is available.

## Troubleshooting
Need help? Contact [Datadog Support][5].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][6]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/gitlab_runner/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/gitlab_runner/metadata.csv
[5]: http://docs.datadoghq.com/help/
[6]: https://www.datadoghq.com/blog/
