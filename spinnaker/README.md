# Agent Check: Spinnaker

## Overview

This check monitors [Spinnaker][1].

Spinnaker is an open source, multi-cloud continuous delivery (CD) platform originally developed by Netflix. It's designed to automate and streamline the software release process, enabling faster and more reliable deployments to the cloud.

This integration integrates Spinnaker with Datadog, providing comprehensive monitoring and visibility across all Spinnaker components. It centralizes logs from Clouddriver, Orca, Redis, Rosco, Deck, and Echo, enabling teams to monitor, analyze, and troubleshoot deployment workflows and infrastructure operations efficiently

### Benefits of Integration:

- **Centralized Monitoring**: Allows customers to view, analyze, and manage all Spinnaker logs in Datadog, improving operational visibility.
- **Enhanced Troubleshooting**: Faster root-cause analysis by centralizing logs for different Spinnaker components, helping resolve issues more quickly.
- **Performance Optimization**: Detailed metrics for pipelines, caching, image baking, etc., allow fine-tuning of workflows and infrastructure management.

### Specific Data Monitored:

- **Infrastructure Changes**: Logs from Clouddriver, valuable for tracking resource management and API performance.
- **Pipeline Status and Errors**: Orca logs provide data on pipeline execution and errors, improving deployment reliability.
- **Cache Performance**: Redis logs monitor caching, helping optimize data retrieval and storage efficiency.
- **Image Creation and Consistency**: Rosco logs ensure smooth image baking, which supports reliable deployment environments.
- **User and Notification Activity**: Deck and Echo logs help track UI activity and notifications, ensuring smooth user experience and reliable alerting.

## Setup

### Installation

**To install the Spinnaker check on your host:**


1. Install the [developer toolkit]
(https://docs.datadoghq.com/developers/integrations/python/)
 on any machine.

2. Run `ddev release build spinnaker` to build the package.

3. [Download the Datadog Agent][2].

4. Upload the build artifact to any host with an Agent and
 run 
`datadog-agent integration install -w
 path/to/spinnaker/dist/<ARTIFACT_NAME>.whl`.

### Configuration

#### Prerequisites

Have your Datadog [API][10] key on hand.

#### Installation
To install the Datadog Agent on a host, use the one-line installation, updated with the Datadog API key from your account:

`DD_API_KEY=<DATADOG_API_KEY> DD_SITE="datadoghq.com" bash -c "$(curl -L https://install.datadoghq.com/scripts/install_script_agent7.sh)"`

- Start the agent using:

`sudo systemctl start datadog-agent`

- Stop the agent using:

`sudo systemctl stop datadog-agent`

- Restart the agent using:

`sudo systemctl restart datadog-agent`


### Validation

Check if the agent is running using: 
- `sudo systemctl status datadog-agent`

- `sudo datadog-agent status`

## Data Collected

### Logs

Spinnaker ingests logs from multiple sources.

### Metrics

Spinnaker does not include any metrics.

### Service Checks

Spinnaker does not include any service checks.

### Events

Spinnaker does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-extras/blob/master/spinnaker/datadog_checks/spinnaker/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-extras/blob/master/spinnaker/metadata.csv
[8]: https://github.com/DataDog/integrations-extras/blob/master/spinnaker/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://app.datadoghq.com/organization-settings/api-keys?_gl=1*ek9ow0*_gcl_au*MTgxNDQ0MjA4Ni4xNzI1NDQwNjkw*_ga*MTg1OTA0NDgzLjE3MjgyODMwOTQ.*_ga_KN80RDFSQK*MTczMDcxNjc0Ni45LjAuMTczMDcxNjc0Ni4wLjAuMjAyMDM0NjYxNQ..*_fplc*JTJCMGolMkY5OVYyJTJGMEUxaE1EUzUlMkJqcEExcUJJMTRiT2R6ZTg5clpqNmdraHJQJTJCbVFMaFAzcHVXS0ZSdE13OVZWMlA2RUllYTRCVW1od0d0JTJCRUhzUEJXaVFucDFja0NacWk4V1pvamJOejFVUUR2QVVKdlI1WVd2azNuSEY1YzR3JTNEJTNE

