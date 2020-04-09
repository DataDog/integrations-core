# OpenLDAP Integration

## Overview

Use the OpenLDAP integration to get metrics from the `cn=Monitor` backend of your OpenLDAP servers.

## Setup

### Installation

The OpenLDAP integration is packaged with the Agent. To start gathering your OpenLDAP metrics:

1. Have the `cn=Monitor` backend configured on your OpenLDAP servers.
2. [Install the Agent][1] on your OpenLDAP servers.

### Configuration

#### Prepare OpenLDAP

If the `cn=Monitor` backend is not configured on your server, follow these steps:

1. Check if monitoring is enabled on your installation:

   ```shell
    sudo ldapsearch -Y EXTERNAL -H ldapi:/// -b cn=module{0},cn=config
   ```

   If you see a line with `olcModuleLoad: back_monitor.la`, monitoring is already enabled, go to step 3.

2. Enable monitoring on your server:

   ```text
       cat <<EOF | sudo ldapmodify -Y EXTERNAL -H ldapi:///
       dn: cn=module{0},cn=config
       changetype: modify
       add: olcModuleLoad
       olcModuleLoad: back_monitor.la
       EOF
   ```

3. Create an encrypted password with `slappasswd`.
4. Add a new user:

   ```text
       cat <<EOF | ldapadd -H ldapi:/// -D <YOUR BIND DN HERE> -w <YOUR PASSWORD HERE>
       dn: <USER_DISTINGUISHED_NAME>
       objectClass: simpleSecurityObject
       objectClass: organizationalRole
       cn: <COMMON_NAME_OF_THE_NEW_USER>
       description: LDAP monitor
       userPassword:<PASSWORD>
       EOF
   ```

5. Configure the monitor database:

   ```text
       cat <<EOF | sudo ldapadd -Y EXTERNAL -H ldapi:///
       dn: olcDatabase=Monitor,cn=config
       objectClass: olcDatabaseConfig
       objectClass: olcMonitorConfig
       olcDatabase: Monitor
       olcAccess: to dn.subtree='cn=Monitor' by dn.base='<USER_DISTINGUISHED_NAME>' read by * none
       EOF
   ```

#### Configure the OpenLDAP integration

##### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

###### Metric collection

1. Edit your `openldap.d/conf.yaml` in the `conf.d` folder at the root of your Agent's configuration directory. See the [sample openldap.d/conf.yaml][2] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param url - string - required
     ## Full URL of your ldap server. Use `ldaps` or `ldap` as the scheme to
     ## use TLS or not, or `ldapi` to connect to a UNIX socket.
     #
     - url: ldaps://localhost:636

       ## @param username - string - optional
       ## The DN of the user that can read the monitor database.
       #
       username: "<USER_DISTINGUISHED_NAME>"

       ## @param password - string - optional
       ## Password associated with `username`
       #
       password: "<PASSWORD>"
   ```

2. [Restart the Agent][3].

###### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `openldap.d/conf.yaml` file to start collecting your OpenLDAP logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/slapd.log
       source: openldap
       service: "<SERVICE_NAME>"
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample openldap.d/conf.yaml][2] for all available configuration options.

3. [Restart the Agent][3].

##### Containerized

###### Metric collection

For containerized environments, see the [Autodiscovery Integration Templates][4] for guidance on applying the parameters below.

| Parameter            | Value                                                                                           |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `openldap`                                                                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                   |
| `<INSTANCE_CONFIG>`  | `{"url":"ldaps://%%host%%:636","username":"<USER_DISTINGUISHED_NAME>","password":"<PASSWORD>"}` |

###### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][5].

| Parameter      | Value                                                 |
| -------------- | ----------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "openldap", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][6] and look for `openldap` under the Checks section.

## Compatibility

The check is compatible with all major platforms.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The openldap check does not include any events.

### Service Checks

**openldap.can_connect**:<br>
Returns `CRITICAL` if the integration cannot bind to the monitored OpenLDAP server, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/openldap/datadog_checks/openldap/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[5]: https://docs.datadoghq.com/agent/kubernetes/log/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/openldap/metadata.csv
[8]: https://docs.datadoghq.com/help
