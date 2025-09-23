# Agent Integration: Delinea Privilege Manager

## Overview

[Delinea Privilege Manager][3] is an endpoint least privilege and application control solution for Windows and macOS, capable of supporting enterprises and fast-growing organizations at scale. Local Security and Application Control are the two major components of Delinea Privilege Manager.

This integration supports the following types of logs:
- **Application Action Events** : Application Action Events contain generic information about the application that ran, the policy that was triggered, the date and time stamp, the computer, and the user.
- **Application Justification Events** : Application Justification Events are generated when an application requiring a justification workflow is run by a user.
- **Bad Rated Application Action Events** : Bad Rated Application Action Events are generated when an application with a poor security rating is being installed or is executed.
- **Password Disclosure Events** : Password Disclosure Events contain any type of password disclosure activity.
- **Newly Discovered File Events** : Newly Discovered File Events contain information about newly discovered files on the system.
- **Change History Events** : Change History Events contain information about any changes made in Delinea Privilege Manager.

View detailed insights into these logs using the out-of-the-box dashboards. The integration also includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Installation

To install the Delinea Privilege Manager integration, run the following Agent installation command followed by the steps below. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not required for Agent version >= 7.63.0.

Linux command
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-delinea-privilege-manager==1.0.0
  ```

### Configuration

#### Log collection

1. By default, log collection is disabled in the Datadog Agent. To enable it, modify the `datadog.yaml` file::

    ```yaml
      logs_enabled: true
    ```
2. Add the following configuration block to your `delinea_privilege_manager.d/conf.yaml` file to start collecting your logs.

    See the sample [delinea_privilege_manager.d/conf.yaml][6] for available configuration options. The appropriate protocol (either TCP or UDP) should be chosen based on the Delinea Privilege Manager syslog forwarding configuration.

    - **TCP**: If TCP protocol is used for syslog forwarding, set the `type` to `tcp`.
    - **UDP**: If UDP protocol is used for syslog forwarding, set the `type` to `udp`.

    ```yaml
      logs:
      - type: <tcp/udp>
        port: <PORT>
        source: delinea-privilege-manager
        service: delinea-privilege-manager
    ```
    **Notes**: 
      - `PORT`: The port should be the same as the one provided in the **Configure syslog message forwarding from Delinea Privilege Manager** section.
      - It is recommended to keep the service and source values unchanged, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][2].

#### Configure syslog message forwarding from Delinea Privilege Manager

  - Creating Syslog server configuration
    1. Navigate to **Admin** > **Configuration** and select the **Foreign Systems** tab.
    2. Click on **Syslog** to open the syslog configurations page, then click on the **Create** button.
    3. Provide a configuration name and the syslog server address (either TCP or UDP)
        - For TCP, the configuration should be formatted like this: tcp://[host]:port
        - For UDP, the configuration should be formatted like this: udp://[host]:port
        
        **host**: IP address where your datadog-agent is running.
        
        **port**: Port number to send syslog messages.
    4. Click on the **Create** button. Confirm the details added and return to the Admin Menu.
  - Setting Up Syslog Server Tasks:
    1. After adding a new Syslog connection, navigate to **Admin** > **Tasks** to send logs to your Syslog Server.
    2. Expand the **Server Tasks** > **Foreign Systems** folders, select **SysLog**, then click **Create**.
    3. From the **Template** drop-down, select the **Send Application Action Events to Syslog** template.
    4. Add a **Name** for this task (set to **Application Action Events**) and **Event Name** (set to **Application Action Events**), and specify the **Event Severity** (0-Lowest, 10-Highest), or keep it as is.

    5. From the **SysLog System** drop-down, select your SysLog server foreign system (configured above).
    6. Provide a value for **Security Ratings Provider** if required, or leave it as is.
    7. Click **Create**.

        **Note**: Do not alter the **Data source**, and ensure the **Replace spaces** toggle is disabled, as any changes to these parameters will directly impact the functionality of the Delinea Privilege Manager integration.

    8. Once created, scroll down to the Schedule section and click on the **New Schedule** button. Provide the following details:
        1. Schedule Details: 
            -  Provide **Schedule Name**.
        2. Schedule:
            1. For **Schedule Type**, select **Shared Schedule** from the drop down.
            2. For **Shared Schedule**, select **Quarter-Hour** from the drop down.
    9. Click on the **Save Changes** button available on the upper-right corner of the page.

This process configures the Syslog forwarding task for **Application Action Events**. For other types of events mentioned in the table below, create new tasks for each event with respective template and event name, and follow all the above steps.

  **Note**: In step 4, make sure to set the **Name** for the task and the **Event Name** according to the selected template, as specified in the table below. The **Event Name** is essential to the functionality of the Delinea Privilege Manager Pipeline and must be provided exactly as specified.

| Template     | Event Name    | Name |
| ---------  | -------------- |--------------
| Send Application Action Events to Syslog | Application Action Events | Application Action Events |
| Send Application Justification Events to Syslog | Application Justification Events | Application Justification Events |
| Send Change History Events to Syslog | Not Applicable | Change History Events |
| Send Newly Discovered File Events to Syslog | Newly Discovered File Events | Newly Discovered File Events |
| Send Password Disclosure Events to Syslog | Password Disclosure Events | Password Disclosure Events |
| Send Bad Rated Application Action Events to Syslog | Bad Rated Application Action Events | Bad Rated Application Action Events |

### Validation

[Run the Agent's status command][5] and look for `Delinea Privilege Manager` under the Checks section.

## Data Collected

### Log 

| Format     | Event Types    |
| ---------  | -------------- |
| CEF | Application Action Events, Bad Rated Application Action Events, Application Justification Events, Password Disclosure Events, Newly Discovered File Events, Change History Events |

### Metrics

The Delinea Privilege Manager integration does not include any metrics.

### Events

The Delinea Privilege Manager integration does not include any events.

### Service Checks

The Delinea Privilege Manager integration does not include any service checks.

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

    **Note**: You must run the `setcap` command every time you upgrade the Agent.

3. [Restart the Agent][2].


**Data is not being collected:**

Ensure traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT_NUMBER> Already in Use** error, see the following instructions. The following example is for port 514:

- On systems using Syslog, if the Agent listens for events on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`. This error occurs because, by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps: 
    - Disable Syslog.
    - Configure the Agent to listen on a different, available port.


For further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://delinea.com/products/privilege-manager
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/delinea_privilege_manager/datadog_checks/delinea_privilege_manager/data/conf.yaml.example
