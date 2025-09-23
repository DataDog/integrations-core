# Agent Integration: Keycloak

## Overview

[Keycloak][3] is an open-source identity and access management tool. It helps add authentication to applications and secure services with minimum effort. Keycloak provides user federation, strong authentication, user management, fine-grained authorization, and more.

This integration parses the following types of logs:
- **user-event** : Events generated from activity of users like authentication, and profile updates.
- **admin-event** : Events generated from the activity of the admin.

Visualize detailed insights into these logs through the out-of-the-box dashboards. Additionally, out-of-the-box detection rules are available to help you monitor and respond to potential security threats effectively.


## Setup

### Installation

To install the Keycloak integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not necessary for Agent version >= 7.63.0.

Linux command
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-keycloak==1.0.0
  ```

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the`datadog.yaml`:

    ```yaml
      logs_enabled: true
    ```
2. Add this configuration block to your `keycloak.d/conf.yaml` file to start collecting your logs.

    See the sample [keycloak.d/conf.yaml][6] for available configuration options. The appropriate protocol (either TCP or UDP) should be chosen based on the Keycloak syslog forwarding configuration. By default, Keycloak uses TCP.

    - **TCP**: If TCP protocol is used for syslog forwarding, set the type to `tcp`.
    - **UDP**: If UDP protocol is used for syslog forwarding, modify the type to `udp`.

    ```yaml
      logs:
      - type: <tcp/udp>
        port: <PORT>
        source: keycloak
        service: keycloak
    ```
    **Note**: 
      - `PORT`: Port should be similar to the port provided in **Configure syslog message forwarding from keycloak** section.
      - It is recommended not to change the service and source values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][2].

#### Configure syslog message forwarding from keycloak

  1. Connect to the remote machine where Keycloak is installed.
  2. Navigate to the directory where Keycloak is installed (typically located at `/opt/keycloak`, depending on the configuration).
  3. Add the following options in the start command to configure Keycloak to forward logs on the Datadog Agent server and execute the same options on the Keycloak server terminal.
  ```
    --log="syslog"
    --log-level=org.keycloak.events:debug
    --log-syslog-endpoint=<IP Address>:<Port>
    --log-syslog-output=json
  ```

  Optional: To use UDP instead of TCP for syslog forwarding, include the following option in the Keycloak start command:

  ```
    --log-syslog-protocol=udp
  ```

  4. After adding the above configuration option, the start command would look like the following:
  ```shell
    bin/kc.[sh|bat] start --log="syslog" --log-syslog-endpoint=<IP Address>:<Port> --log-level=org.keycloak.events:debug --log-syslog-output=json
  ```
  `IP ADDRESS`: IP address where your Datadog Agent is running.
  
  `PORT`: Port number to send syslog messages.

  Reference: [Keycloak Syslog Configuration][7] 

### Validation

[Run the Agent's status subcommand][5] and look for `keycloak` under the Checks section.

## Data Collected

### Log 

| Format     | Event Types    |
| ---------  | -------------- |
| JSON | user-event, admin-event |

### Metrics

The Keycloak integration does not include any metrics.

### Events

The Keycloak integration does not include any events.

### Service Checks

The Keycloak integration does not include any service checks.

## Troubleshooting

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs:

1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:
    ```shell
    sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
    ```

2. Verify the setup is correct by running the `getcap` command:

    ```shell
    sudo getcap /opt/datadog-agent/bin/agent/agent
    ```

    With the expected output:

    ```shell
    /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
    ```

    **Note**: Re-run this `setcap` command every time you upgrade the Agent.

3. [Restart the Agent][2].


**Data is not being collected:**

Ensure traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT_NUMBER> Already in Use** error, see the following instructions. The following example is for port 514:

- On systems using Syslog, if the Agent listens for events on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`. This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps: 
    - Disable Syslog.
    - Configure the Agent to listen on a different, available port.


For further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://www.keycloak.org/
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/keycloak/datadog_checks/keycloak/data/conf.yaml.example
[7]: https://www.keycloak.org/server/logging
