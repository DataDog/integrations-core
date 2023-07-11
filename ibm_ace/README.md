# Agent Check: IBM ACE

## Overview

This check monitors [IBM ACE][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### IBM MQ

An [IBM MQ][10] server is required for consuming metric messages from IBM ACE.

<div class="alert alert-warning">
For Linux, make sure to set the LD_LIBRARY_PATH environment variable as described in the <a href="https://docs.datadoghq.com/integrations/ibm_mq/">IBM MQ setup</a> before continuing.
</div>

### IBM ACE

1. Ensure at least version 12.0.2.0 is installed.
2. Apply an [MQEndpoint policy][11] file named in the form `<MQ_POLICY_NAME>.policyxml` that would look like this:
    ```xml
    <?xml version="1.0" encoding="UTF-8"?>
    <policies>
        <policy policyType="MQEndpoint" policyName="<MQ_POLICY_NAME>" policyTemplate="MQEndpoint">
            <connection>CLIENT</connection>
            <destinationQueueManagerName>...</destinationQueueManagerName>
            <queueManagerHostname>...</queueManagerHostname>
            <listenerPortNumber>1414</listenerPortNumber>
            <channelName>...</channelName>
            <securityIdentity><MQ_SECURITY_IDENTITY></securityIdentity>
        </policy>
    </policies>
    ```
3. [Set][12] the credentials by running: `mqsisetdbparms -n mq::<MQ_SECURITY_IDENTITY> -u <user> -p <password>`
4. Update your `server.conf.yaml` file with the following config:
    ```yaml
    remoteDefaultQueueManager: '{DefaultPolicies}:<MQ_POLICY_NAME>'
    Events:
      OperationalEvents:
        MQ:
          enabled: true
      BusinessEvents:
        MQ:
          enabled: true
          outputFormat: json
    Statistics:
      Resource:
        reportingOn: true
      Snapshot:
        publicationOn: active
        outputFormat: json
        accountingOrigin: basic
        nodeDataLevel: advanced
        threadDataLevel: basic
    Monitoring:
      MessageFlow:
        publicationOn: active
        eventFormat: MonitoringEventV2
    AdminLog:
      enabled: true
      fileLog: true
      consoleLog: true
      consoleLogFormat: ibmjson
    ```
5. Restart IBM ACE.

### Installation

The IBM ACE check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `ibm_ace.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your ibm_ace performance data. See the [sample ibm_ace.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `ibm_ace` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The IBM ACE integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. To start collecting your IBM ACE logs, add this configuration block to your `ibm_ace.d/conf.yaml` file:

    ```yaml
    logs:
      - type: file
        path: /home/aceuser/ace-server/log/integration_server.txt
        source: ibm_ace
    ```

    Change the `path` parameter value based on your environment. See the [sample `ibm_ace.d/conf.yaml` file][4] for all available configuration options.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.ibm.com/docs/en/app-connect/12.0?topic=overview-app-connect-enterprise-introduction
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/ibm_ace/datadog_checks/ibm_ace/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ibm_ace/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/ibm_ace/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.ibm.com/products/mq
[11]: https://www.ibm.com/docs/en/app-connect/12.0?topic=properties-mqendpoint-policy
[12]: https://www.ibm.com/docs/en/app-connect/12.0?topic=mq-connecting-secured-queue-manager
