## Overview

[BeyondTrust Privileged Remote Access][3] securely manages and controls remote access to critical systems for privileged users, such as administrators, IT personnel, and third-party vendors.

Integrate BeyondTrust Privileged Remote Access with Datadog to gain insights into BeyondTrust Privileged Remote Access logs using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. The integration can also be used for Cloud SIEM detection rules for enhanced monitoring and security.

**Minimum Agent version:** 7.76.0

## Setup

### Prerequisites
- `rsyslog` (version 8.2302 or higher) with valid TLS certificates present on the server.

### Configuration

#### Configure File Rotation Script

1. Create the script file.
    ```shell
    sudo mkdir -p /etc/rsyslog.d/scripts
    sudo vi /etc/rsyslog.d/scripts/file_rotate.sh
    ```

2. Add the following content to the script:
    ```shell
    #!/bin/bash

    LOGFILE="/var/log/rsyslog_logs/beyondtrust_pra.log"

    last_line=$(tail -n 1 "$LOGFILE")

    num1=$(echo "$last_line" | grep -oE '[0-9]+:[0-9]+:[0-9]+' | tail -n 1 | cut -d: -f2)
    num1=$(printf "%d" "$num1")
    LAST_LINES=$(tail -n "$num1" "$LOGFILE")

    # Capture permissions, owner, group
    PERMS=$(stat -c "%a" "$LOGFILE")
    OWNER=$(stat -c "%U" "$LOGFILE")
    GROUP=$(stat -c "%G" "$LOGFILE")

    # Remove the original file
    rm -f "$LOGFILE"

    # Recreate file with same permissions
    touch "$LOGFILE"
    chmod "$PERMS" "$LOGFILE"
    chown "$OWNER:$GROUP" "$LOGFILE"

    # Write back the last lines
    printf "%s\n" "$LAST_LINES" > "$LOGFILE"
    ```

3. Set Ownership and Permissions for Scripts
    ```shell
    sudo chown -R syslog:syslog /etc/rsyslog.d/scripts
    sudo chmod 777 /etc/rsyslog.d/scripts
    sudo chmod 500 /etc/rsyslog.d/scripts/file_rotate.sh
    ```

#### Certificate Directory Setup

Store the TLS certificates in the directory using the file names mentioned in the table below. These files will be referenced directly in the rsyslog configuration.

```shell
sudo mkdir -p /etc/rsyslog.d/certs
```

| Filename       | Description                                                                          |
|----------------|--------------------------------------------------------------------------------------|
| rootCA.pem     | Certificate authority (CA) certificate that signed the rsyslog server certificate.   |
| fullchain.pem  | rsyslog server certificate along with any required intermediate certificates.        |
| server.key     | Private key corresponding to the rsyslog server certificate                          |

Set ownership and permissions so that the syslog user can access the certificates.

```shell
sudo chown -R syslog:syslog /etc/rsyslog.d/certs
sudo chmod -R 500 /etc/rsyslog.d/certs
```

#### Configure rsyslog
1. Open the main configuration file.
    ```shell
    sudo vi /etc/rsyslog.conf
    ```
2. Add the following TLS settings to receive BeyondTrust PRA logs:  
   Replace the `<RSYSLOG_TCP_PORT>`, `<DATADOG_AGENT_IP>`, and `<DATADOG_AGENT_PORT>` with actual values.
    ```shell    
    module(load="imfile")

    $ActionFileDefaultTemplate RSYSLOG_TraditionalFileFormat
    $FileCreateMode 0640
    $DirCreateMode 0550
    $Umask 0022

    $MaxMessageSize 64k
    $IncludeConfig /etc/rsyslog.d/*.conf

    global(
      DefaultNetstreamDriver="gtls"
      DefaultNetstreamDriverCAFile="/etc/rsyslog.d/certs/rootCA.pem"
      DefaultNetstreamDriverCertFile="/etc/rsyslog.d/certs/fullchain.pem"
      DefaultNetstreamDriverKeyFile="/etc/rsyslog.d/certs/server.key"
    )

    module(
      load="imtcp"
      StreamDriver.Name="gtls"
      StreamDriver.Mode="1"
      StreamDriver.Authmode="anon"
    )

    input(
    type="imtcp"
    port="<RSYSLOG_TCP_PORT>"
    ruleset="write_to_file"
    )

    input(
      type="imfile"
      File="/var/log/rsyslog_logs/beyondtrust_pra.log"
      readTimeout="30"
      startmsg.regex="(<[0-9]+>)?[A-Za-z]{3}[[:space:]]+[0-9]{1,2}[[:space:]]+[0-9]{2}:[0-9]{2}:[0-9]{2}[[:space:]]+[^[:space:]]+[[:space:]]+[A-Z]+\\[[0-9]+\\][[:space:]]+[0-9]+:01.*"
      ruleset="forward_merged"
      Tag="agg:"
      Facility="local0"
    )

    ruleset(name="write_to_file") {
      action(
        type="omfile"
        file="/var/log/rsyslog_logs/beyondtrust_pra.log"
        createDirs="on"
        rotation.sizeLimit="50000000"  # 50 MB
        rotation.sizeLimitCommand="/etc/rsyslog.d/scripts/file_rotate.sh"
      )
    }

    template(name="log_message" type="string" string="%msg%\n")
    ruleset(name="forward_merged") {
      action(type="omfwd" target="<DATADOG_AGENT_IP>" port="<DATADOG_AGENT_PORT>" protocol="tcp" template="log_message")
    }
    ```
3. Restart the rsyslog server
    ```shell
    sudo systemctl restart rsyslog
    ```

#### Log Collection
1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `beyondtrust_privileged_remote_access.d/conf.yaml` file to start collecting your BeyondTrust Privileged Remote Access logs:

    ```yaml
    logs:
      - type: tcp
        port: <PORT>
        source: beyondtrust-privileged-remote-access
        service: beyondtrust-privileged-remote-access
        log_processing_rules:
          - type: include_at_match
            name: include_pra_logs
            pattern: 'BG'
          - type: mask_sequences
            name: remove_subsequent_segment_headers
            replace_placeholder: ""
            pattern: '\\n(<\d+>)?\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\w+\s+[A-Z]+\[\d+\]\s+\d+:([0-9])?[2-9]+:\d+:'
    ```
    See the sample configuration file ([beyondtrust_privileged_remote_access.d/conf.yaml][5]) for available options.

    **Note**: Do not change the `source` and `service` values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][2].

### Configure syslog message forwarding from BeyondTrust Privileged Remote Access
1. Sign in to the [**BeyondTrust B Series Appliance**][6].
2. From the top navigation menu, go to **Security > Appliance Administration**.
3. Enter the following details for the syslog configuration:
    - **Remote Syslog Server:** Enter the IP address or hostname of the rsyslog server.
    - **Message Format:** Select **Syslog over TLS (RFC 5425)**.
    - **Port:** Specify the port number on which the rsyslog server is listening.
    - **Trusted Certificate:** Upload the `rootCA.pem` certificate, which is used to secure the TLS connection to the rsyslog server.
4. Click **Submit**.

### Validation

[Run the Agent's status subcommand][4] and look for `beyondtrust-privileged-remote-access` under the Logs Agent section.

## Data Collected

### Logs

The BeyondTrust Privileged Remote Access integration collects `Authentication & Authorization`, `User & Account Management`, `Group & Policy Management`, `Jumpoint & Remote Access Management`, `Network Configuration`, `Cryptography & Secrets Protection`, `Reporting & Compliance Evidence`, and `API & Integration Management` logs.

### Metrics

The BeyondTrust Privileged Remote Access does not include any metrics.

### Events

The BeyondTrust Privileged Remote Access integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/ 
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://www.beyondtrust.com/products/privileged-remote-access
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/beyondtrust_privileged_remote_access/datadog_checks/beyondtrust_privileged_remote_access/data/conf.yaml.example
[6]: https://app.beyondtrust.io/pra/login/appliance
