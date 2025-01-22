# Agent Check: Tibco EMS

## Overview

This check monitors [TIBCO Enterprise Message Service][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The TIBCO EMS check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Edit the `tibco_ems.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your TIBCO EMS performance data. See the [sample tibco_ems.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Metric collection

##### Create your Tibco EMS command script

The Tibco EMS integration utilizes the `tibemsadmin` CLI tool provided by Tibco EMS. To reduce the number of calls to the `$sys.admin` queue, Datadog uses a script to batch the queries made to Tibco. To collect your Tibco EMS metrics, pass the the script path and the absolute path of the `tibemsadmin` binary to the integration configuration.

*Note*: The `dd-agent` user needs execute permissions on the `tibemsadmin` binary.
1. Create a file named `show_commands` with the following contents:
```text
    show connections full
    show durables
    show queues
    show server
    show stat consumers
    show stat producers
    show topics
```


2. Add this configuration block to your `tibco_ems.d/conf.yaml` file to start gathering [Tibco EMS metrics](#metrics):

```yaml
init_config:
instances:
    ## @param script_path - string - optional
    ## The path to the script that will be executed to collect metrics. Since the script is executed by a subprocess,
    ## we need to know the path to the script. This must be the absolute path to the script.
    #
    script_path: <SCRIPT_PATH>

    ## @param tibemsadmin - string - optional
    ## The command or path to tibemsadmin (for example /usr/bin/tibemsadmin or docker exec <container> tibemsadmin)
    ## , which can be overwritten on an instance.
    ##
    ## This overrides `tibemsadmin` defined in `init_config`.
    #
    tibemsadmin: <TIBEMSADMIN>
```

3. [Restart the Agent][5] to begin sending Tibco EMS metrics to Datadog.

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent. Enable logs in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `tibco_ems.d/conf.yaml` file to start collecting your Tibco EMS logs:

   ```yaml
   logs:
     - type: file
       path: <PATH_TO_LOG_FILE>
       service: <MY_SERVICE>
       source: tibco_ems
   ```

    Change the `service` and `path` parameter values and configure them for your environment. See the [sample tibco_ems.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `tibco_ems` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The TIBCO EMS integration does not include any events.

### Service Checks

The TIBCO EMS integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://docs.tibco.com/products/tibco-enterprise-message-service
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/tibco_ems/datadog_checks/tibco_ems/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/tibco_ems/metadata.csv
[8]: https://docs.datadoghq.com/help/
