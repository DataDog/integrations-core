# Supply Chain Firewall

## Overview

[Supply Chain Firewall][1] is a command-line tool designed to prevent the installation of malicious packages from PyPI and npm. It is primarily intended for engineers to safeguard their development workstations against supply-chain attacks and reduce the risk of compromise during software development.

Integrate Supply Chain Firewall with Datadog's pre-built dashboard visualizations to gain insights into Package Manager logs. With Datadog's built-in log pipelines, you can parse and enrich these logs to facilitate easy search and detailed insights. Additionally, the integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.


**Minimum Agent version:** 7.69.1

## Setup

### Configuration

1. Execute the following command to start configuration for Supply Chain Firewall:

    ```bash
    scfw configure
    ```

2. Follow the setup prompts and configure the options as needed. During the log forwarding configuration, choose one of the options below to send logs to Datadog, based on your preferences:

    - **Option 1: Sending Logs through the Datadog Agent**

        - Configure log forwarding through the Datadog Agent:
            ```text
            [?] If you have the Datadog Agent installed locally, would you like to forward firewall logs to it? (y/N): y
            [?] Enter the local port where the Agent will receive logs (default: 10365): <PORT>
            [?] Select the desired log level for Datadog logging:
            > Log allowed and blocked commands
            ```
            This will automatically create the `scfw.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][5], using the provided port for TCP log forwarding.  

        - Log collection is disabled by default in the Datadog Agent. Enable it by editing the `datadog.yaml` file:

            ```yaml
            logs_enabled: true
            ```

        - Restart the agent to begin accepting firewall logs:

            ```bash
            sudo systemctl restart datadog-agent
            ```

    - **Option 2: Sending Logs through an API Key**

        - Configure log forwarding using the Datadog API key:
            ```text
            [?] If you have the Datadog Agent installed locally, would you like to forward firewall logs to it? (y/N): N
            [?] Would you like to enable sending firewall logs to Datadog using an API key? (y/N): y
            [?] Enter a Datadog API key: <DATADOG_API_KEY>
            [?] Select the desired log level for Datadog logging:
            > Log allowed and blocked commands
            ```
        - By default, the Datadog instance site is set to `us1`. If your instance uses a different site, set the `DD_SITE` environment variable accordingly using the appropriate `Site Parameter` from the [Datadog site documentation][3].

3. After setup, update your current shell environment:

    - For **Bash**:

        ```bash
        source ~/.bashrc
        ```

    - For **Zsh**:

        ```bash
        source ~/.zshrc
        ```


### Validation

If you selected **Option 1** to forward logs through the Datadog Agent, [run the Agent's status subcommand][2] and look for `scfw` under the Logs Agent section.

## Data Collected

### Logs

The Supply Chain Firewall integration collects and forwards Package Manager logs to Datadog.

### Metrics

The Supply Chain Firewall integration does not include any metrics.

### Events

The Supply Chain Firewall integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://github.com/DataDog/supply-chain-firewall
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site
[4]: https://docs.datadoghq.com/help/
[5]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
