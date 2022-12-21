# Agent Check: Cloudera

## Overview

This integration monitors your [Cloudera Data Platform][1] through the Datadog Agent, allowing you to submit metrics and service checks on the health of your Cloudera Data Hub clusters, hosts, and roles.  

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Cloudera check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Prepare Cloudera Manager
1. In Cloudera Data Platform, navigate to the Management Console and click on the **User Management** tab.
![User Management][10]

2. Click on **Actions**, then **Create Machine User** to create the machine user that queries the Cloudera Manager through the Datadog Agent.
![Create Machine User][11]

3. If the workload password hasn't been set, click on **Set Workload Password** after the user is created.
![Set Workload Password][12]

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host
1. Edit the `cloudera.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Cloudera cluster and host data. See the [sample cloudera.d/conf.yaml][4] for all available configuration options. Note that the `api_url` should contain the API version at the end.

   ```yaml
   init_config:

      ## @param workload_username - string - required
      ## The Workload username. This value can be found in the `User Management` tab of the Management 
      ## Console in the `Workload User Name`.
      #
      workload_username: <WORKLOAD_USERNAME>

      ## @param workload_password - string - required
      ## The Workload password. This value can be found in the `User Management` tab of the Management 
      ## Console in the `Workload Password`.
      #
      workload_password: <WORKLOAD_PASSWORD>

   ## Every instance is scheduled independently of the others.
   #
   instances:

      ## @param api_url - string - required
      ## The URL endpoint for the Cloudera Manager API. This can be found under the Endpoints tab for 
      ## your Data Hub to monitor. 
      ##
      ## Note: The version of the Cloudera Manager API needs to be appended at the end of the URL. 
      ## For example, using v48 of the API for Data Hub `cluster_1` should result with a URL similar 
      ## to the following:
      ## `https://cluster1.cloudera.site/cluster_1/cdp-proxy-api/cm-api/v48`
      #
      - api_url: <API_URL>
   ```

2. [Restart the Agent][5] to start collecting and sending Cloudera Data Hub cluster data to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

| Parameter            | Value                                                                                                            |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `cloudera`                                                                                                       |
| `<INIT_CONFIG>`      | `{"workload_username": "<WORKLOAD_USERNAME>", 'workload_password": "<WORKLOAD_PASSWORD>"}`                       |
| `<INSTANCE_CONFIG>`  | `{"api_url": <API_URL>"}`                                                                                        |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][6] and look for `cloudera` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Cloudera integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.cloudera.com/products/cloudera-data-platform.html
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/cloudera/datadog_checks/cloudera/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cloudera/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/cloudera/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cloudera/images/user_management.png
[11]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cloudera/images/create_machine_user.png
[12]: https://raw.githubusercontent.com/DataDog/integrations-core/master/cloudera/images/set_workload_password.png
