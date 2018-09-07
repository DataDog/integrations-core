# OpenLDAP Integration

## Overview

Use the OpenLDAP integration to get metrics from the `cn=Monitor` backend of your OpenLDAP servers.

## Setup

### Installation

The OpenLDAP integration is packaged with the Agent. To start gathering your OpenLDAP metrics, you need to:

1. Have the `cn=Monitor` backend configured on your OpenLDAP servers.
2. [Install the Agent][1] on your OpenLDAP servers.

### Configuration

#### Prepare OpenLDAP

If the `cn=Monitor` backend is not configured on your server, follow these steps:

1. Check if monitoring is enabled on your installation

    ```
        sudo ldapsearch -Y EXTERNAL -H ldapi:/// -b cn=module{0},cn=config
    ```

If you see a line with `olcModuleLoad: back_monitor.la`, monitoring is already enabled, go to step 3.

2. Enable monitoring on your server

    ```
        cat <<EOF | sudo ldapmodify -Y EXTERNAL -H ldapi:///
        dn: cn=module{0},cn=config
        changetype: modify
        add: olcModuleLoad
        olcModuleLoad: back_monitor.la
        EOF
    ```

3. Create a user for accessing the monitoring information

    1. Create an encrypted password with `slappasswd`
    2. Add a new user

        ```
            cat <<EOF | ldapadd -H ldapi:/// -D <YOUR BIND DN HERE> -w <YOUR PASSWORD HERE>
            dn: <DN OF THE NEW USER>
            objectClass: simpleSecurityObject
            objectClass: organizationalRole
            cn: <COMMON NAME OF THE NEW USER>
            description: LDAP monitor
            userPassword:<ENCRYPTED PASSWORD HERE>
            EOF
        ```

4. Configure the monitor database

    ```
        cat <<EOF | sudo ldapadd -Y EXTERNAL -H ldapi:///
        dn: olcDatabase=Monitor,cn=config
        objectClass: olcDatabaseConfig
        objectClass: olcMonitorConfig
        olcDatabase: Monitor
        olcAccess: to dn.subtree='cn=Monitor' by dn.base='<YOUR MONITOR USER DN HERE>' read by * none
        EOF
    ```

#### Configure the OpenLDAP integration

Add this configuration block to your `openldap.yaml` file to start gathering your [metrics](#metrics):

```
  init_config:

  instances:
      - url: ldaps://localhost
        port: 686
        username: <your monitor user DN>
        password: <your monitor user password>
```

See the [sample openldap.yaml][2] for all available configuration options.

[Restart the Agent][3] to begin sending OpenLDAP metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `openldap` under the Checks section:

```
  Checks
  ======
    [...]

    openldap
    --------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The check is compatible with all major platforms.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The openldap check does not include any event at this time.

### Service Checks

**openldap.can_connect**

Returns `CRITICAL` if the integration cannot bind to the monitored OpenLDAP server, `OK` otherwise.

## Troubleshooting

Need help? Contact [Datadog Support][7].

## Development

Please refer to the [main documentation][6]
for more details about how to test and develop Agent based integrations.

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/openldap/datadog_checks/openldap/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/openldap/metadata.csv
[6]: https://docs.datadoghq.com/developers/
[7]: https://docs.datadoghq.com/help/