# Microsoft SCOM Datadog Integration

## Overview
[Microsoft SCOM][1] is a service that helps you monitor and manage your IT environment.

This integration enables Datadog to collect information from Microsoft SCOM, including alerts, events, tasks, and discovery data, as well as details about management servers, agentless managed computers, agents, and groups. It provides six out-of-the-box dashboards that give you real-time visibility into your SCOM environment, helping you monitor infrastructure health, track incidents, and analyze trends directly within Datadog.

### Dashboards
- Microsoft SCOM - Alerts
- Microsoft SCOM - Events
- Microsoft SCOM - Discoveries and Tasks
- Microsoft SCOM - Groups
- Microsoft SCOM - Management Servers
- Microsoft SCOM - Agents and Agentless Managed Computers

## Setup

> **Note**: A [detailed version of these instructions][2] and an [FAQ][3] are also available.

### Prerequisites
Before setting up this integration, ensure your environment meets the following prerequisites:

- The Datadog Agent must be installed and running on the SCOM server. For more information, see the [Datadog Agent][4] documentation.
- The ddagentuser account must have **Administrator** privileges in SCOM for this integration.
- The user must be a member of the **Administrators** group or the **Domain Admins** group on the **Active Directory server**.
- The following services must be running on the SCOM Management Server: **HealthService** (System Center Management), **OpsMgrSdkSvc** (System Center Data Access Service), **OMConfigService** (System Center Management Configuration), **MMAgent** (Microsoft Monitoring Agent), and **SQL Server** (MSSQLSERVER or the relevant named instance).

### Granting `ddagentuser` Administrator Privileges in SCOM
Follow these steps to ensure the `ddagentuser` account has the required permissions:

1. **Open the SCOM Console**  
   - Launch the **Operations Manager Console** on the SCOM management server.

2. **Navigate to User Roles**  
   - In the left pane, go to **Administration** > **Security** > **User Roles**.

3. **Edit a User Role**  
   - Click **User Roles**, then select **Administrator**.
   - Right-click **Administrator** and choose **Properties**.

4. **Add the `ddagentuser` Account**  
   - In the **Users** tab, click **Add**.
   - **Determine the Hostname**  
     - On the SCOM server, open a command prompt or PowerShell window.  
     - Run `hostname` to get the computer name (the host). 
     - Combine them in the format `HOSTNAME\ddagentuser`.
   - Enter the username as `HOSTNAME\ddagentuser` (replace `HOSTNAME` with the host you retrieved) and click **OK**.

5. **Save Changes**  
   - Confirm the addition and click **OK** to apply the changes.

6. **Verify Membership**  
   - Ensure `ddagentuser` now appears in the **Administrator** role members list.

> The `ddagentuser` account now has the required **Administrator** privileges in SCOM for the Datadog integration.


### Installation

- To install the integration, run the following command:
    
    - Windows:
        ```sh 
        "%ProgramFiles%\Datadog\Datadog Agent\bin\agent.exe" integration install --third-party datadog-crest_data_systems_microsoft_scom==1.0.0
        ```

- Install the required Python packages by running the following commands:

    - Windows:

        ```
        "%programfiles%\Datadog\Datadog Agent\embedded3\python.exe" -m pip install "datadog-api-client>=2.16.0"
        ```

        ```
        "%programfiles%\Datadog\Datadog Agent\embedded3\python.exe" -m pip install "datadog-checks-base>=37.20.0"
        ```      

### Configuration
#### Parameter descriptions
This integration provides the following configuration parameters:

- `min_collection_interval` (required): Sets the frequency (in seconds) at which data is collected.
- `collect_data` (optional): Provide the entities to fetch data from Microsoft SCOM.

#### Set up `datadog.yaml`
1. You must set `app_key` and `api_key` in `datadog.yaml` if they are not already configured. For more information, see [Agent Configuration Files][5] and [API and Application Keys][6].

   ```yaml
        ## @param api_key - string - required
        ## Datadog API Key
        #
        api_key: <API_KEY>

        ## @param app_key - string - required
        ## Datadog App Key
        #
        app_key: <APP_KEY>

        ## @param site - string - optional - default: datadoghq.com
        ## @env DD_SITE - string - optional - default: datadoghq.com
        ## The site of the Datadog intake to send Agent data to.
        ## Set to 'datadoghq.eu' to send data to the EU site.
        ## Set to 'us3.datadoghq.com' to send data to the US3 site.
        ## Set to 'us5.datadoghq.com' to send data to the US5 site.
        ## Set to 'ddog-gov.com' to send data to the US1-FED site.
        #
        site: <URL>
   ```

2. The `logs_enabled` setting needs to be configured in the `datadog.yaml` file if it is not already set to collect **logs**. For more information, see [Agent Configuration Files][5].
   ```yaml
      ## @param logs_enabled - boolean - optional - default: false
      ## Enable Datadog Agent to log collection by setting logs_enabled to true.
      #
      logs_enabled: true
   ```

#### Set up `conf.yaml`

1. Copy the `conf.yaml.example` file to `conf.yaml`:

   - Windows: Copy the `conf.yaml.example` file from:

     ```
     %ProgramData%\Datadog\conf.d\crest_data_systems_microsoft_scom.d\conf.yaml.example
     ```

     to:

     ```
     %ProgramData%\Datadog\conf.d\crest_data_systems_microsoft_scom.d\conf.yaml
     ```

2. Open the `crest_data_systems_microsoft_scom.d/conf.yaml` file in a text editor and configure the following parameters:
    ```yaml
   ## All options defined here are available to all instances.
   #
   init_config:

      ## @param service - string - optional
      ## Attach the tag `service:<SERVICE>` to every metric, event, and service check emitted by this integration.
      ##
      ## Additionally, this sets the default `service` for every log source.
      #
      # service: <SERVICE>

   ## Log Section
   ##
   ## type - required - Type of log input source (tcp / udp / file / windows_event).
   ## port / path / channel_path - required - Set port if type is tcp or udp.
   ##                                         Set path if type is file.
   ##                                         Set channel_path if type is windows_event.
   ## source  - required - Attribute that defines which integration sent the logs.
   ## encoding - optional - For file specifies the file encoding. Default is utf-8. Other
   ##                       possible values are utf-16-le and utf-16-be.
   ## service - optional - The name of the service that generates the log.
   ##                      Overrides any `service` defined in the `init_config` section.
   ## tags - optional - Add tags to the collected logs.
   ##
   ## Discover Datadog log collection: https://docs.datadoghq.com/logs/log_collection/
   #
   logs:
   - type: integration
     source: crest-data-systems-microsoft-scom

   ## Every instance is scheduled independently of the others.
   #
   instances:

   -
      ## @param collect_data - list of strings - optional - default: ['alerts', 'events', 'task_results', 'discovery', 'agents', 'agentless_managed_computers', 'management_servers', 'groups']
      ## Provide the entities to fetch. Please specify the exact values as mentioned in the default list.
      #
      # collect_data:
      #   - alerts
      #   - events
      #   - task_results
      #   - discovery
      #   - agents
      #   - agentless_managed_computers
      #   - management_servers
      #   - groups

      ## @param min_collection_interval - number - required
      ## This changes the collection interval of the check. For more information, see:
      ## https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
      #
      min_collection_interval: 3600
    ```
    Example `conf.yaml` file:
    ```yaml
    init_config:
    logs:
      - type: integration
        source: crest-data-systems-microsoft-scom
    instances:
      - collect_data:
         - alerts
         - events
        min_collection_interval: 3600
    ```
3. [Restart the Datadog Agent][7].

### Validation

[Run the Agent's status subcommand][8] and look for `crest_data_systems_microsoft_scom` under the Checks section.

For more detailed logs, run:
- Windows:
  ```powershell
  "%ProgramFiles%\Datadog\Datadog Agent\bin\agent.exe" check crest_data_systems_microsoft_scom --log-level debug
  ```

## Uninstallation

To remove the integration from the Datadog Agent:

- Windows:
  ```sh
  "%ProgramFiles%\Datadog\Datadog Agent\bin\agent.exe" integration remove datadog-crest_data_systems_microsoft_scom
  ```

### YAML config cleanup

- If you plan to reinstall or keep the config files, go to your Agent's `conf.d` directory and locate the `crest_data_systems_microsoft_scom.d` folder to retain the `conf.yaml`.

- If you plan to fully uninstall (including removing the configuration), remove the `crest_data_systems_microsoft_scom.d` folder from your Agent's `conf.d` directory.

To cancel your plan:

1. From the Microsoft SCOM tile, navigate to the **Plan & Pricing** tab.
2. Select **Modify Plan**, click **Cancel Plan**, and complete the cancellation flow.

## Support
For support or feature requests, contact Crest Data through the following channels:

- Support email: [datadog.integrations@crestdata.ai][9]
- Sales email: [datadog-sales@crestdata.ai][10]
- Website: [crestdata.ai][11]
- FAQ: [Crest Data Datadog Marketplace Integrations FAQ][3]


[1]: https://www.microsoft.com/en-in/system-center
[2]: https://docs.crestdata.ai/datadog-integrations-readme/Microsoft_SCOM.pdf
[3]: https://docs.crestdata.ai/datadog-integrations-readme/Crest_Data_Datadog_Integrations_FAQ.pdf
[4]: https://docs.datadoghq.com/agent/?tab=Linux
[5]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/#main-configuration-file
[6]: https://docs.datadoghq.com/account_management/api-app-keys
[7]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[9]: mailto:datadog.integrations@crestdata.ai
[10]: mailto:datadog-sales@crestdata.ai
[11]: https://www.crestdata.ai/