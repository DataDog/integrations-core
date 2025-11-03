# Guarddog

## Overview

[GuardDog][4] is a CLI tool that allows identifying malicious PyPI and npm packages, Go modules, and GitHub actions. It runs a set of heuristics on the package source code (through Semgrep rules) and on the package metadata.

This integration monitors configured dependency files using Guarddog scans and sends the scan output to Datadog for analysis, providing visual insights through out-of-the-box dashboards and the Log Explorer. It also helps monitor and respond to security threats with ready-to-use Cloud SIEM detection rules.

**Note:**
- **Minimum Agent version:** 7.73.0

## Setup

### Installation

The Guarddog check is already included with the [Datadog Agent][7] package, so no extra installation is required.

### Configuration

#### Install Guarddog

  Note: 
      - Guarddog requires python version 3.10 or higher.
      - The Datadog Agent must have access to the Guarddog executable path.

1. Install Guarddog using pip:
    ```shell
    pip3 install guarddog
    ```
2. Run this command to find the Guarddog executable path:
    ```shell
    which guarddog
    ```
    This path is required for the **guarddog_path** parameter in **guarddog.d/conf.yaml** file.


#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `guarddog.d/conf.yaml` file to start monitoring dependency files using guarddog. See the sample [guarddog.d/conf.yaml][6] for available configuration options.

      ```yaml
      logs:
        - type: integration
          service: guarddog
          source: guarddog

      init_config:
          ## @param guarddog_path - string - required
          ## Absolute path to the Guarddog file. Example: /usr/local/bin/guarddog
          #
          guarddog_path: <ABSOLUTE_PATH_OF_GUARDDOG>

      instances:
          ## @param package_ecosystem - string - required
          ## The type of package ecosystem. Supported values: pypi, npm, go and github_action
          #
        - package_ecosystem: <PACKAGE_ECOSYSTEM>
          ## @param dependency_file_path - string - required
          ## Absolute path to the dependency file you want to monitor. Example: /app/requirements.txt
          #
          dependency_file_path: <DEPENDENCY_FILE_PATH>
          ## @param min_collection_interval - number - required
          ## This changes the collection interval of the check. Default value is 86400 seconds(1 day). For more information, see:
          ## https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
          #
          min_collection_interval: 86400
      ```

      **Note:**
      - It is recommended not to change the service and source values, as these parameters are integral to the pipeline's operation.
      - To track more than one dependency file, add additional entries under the instances as below:
        ```yaml
        instances:
          - package_ecosystem: pypi
            dependency_file_path: /app/requirements.txt
            min_collection_interval: 86400
          - package_ecosystem: npm
            dependency_file_path: /app/package.json
            min_collection_interval: 86400
          - package_ecosystem: go
            dependency_file_path: /app/go.mod
            min_collection_interval: 86400
          - package_ecosystem: github_action
            dependency_file_path: /app/action.yml
            min_collection_interval: 86400
        ```

3. Ensure the **dd-agent** user has read access to all dependency files you configure and traverse permission on every parent directory in the file path.
4. [Restart the Agent][1].

### Validation

[Run the Agent's status subcommand][2] and look for `guarddog` under the Checks section.

## Data Collected

### Logs

The Guarddog integration collects scan logs.

### Metrics

The Guarddog integration does not include any metrics.

### Events

The Guarddog integration does not include any events.

## Troubleshooting

For any further assistance, contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/help/
[4]: https://github.com/DataDog/guarddog
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://github.com/DataDog/integrations-core/blob/master/guarddog/datadog_checks/guarddog/data/conf.yaml.example
[7]: https://app.datadoghq.com/account/settings/agent/latest