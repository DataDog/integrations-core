## Overview

[PingFederate][3] is an enterprise-grade identity federation server that provides secure single sign-on (SSO), multi-factor authentication (MFA), and federated identity management across various applications and services.


This integration provides enrichment and visulization for admin and audit logs. It helps to visualize detailed insights into admin and audit log analysis using out-of-the-box dashboards.

## Setup

### Installation

To install the PingFederate integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not necessary for Agent version >= 7.54.0.

Linux command
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-ping_federate==1.0.0
  ```


### Configuration

### Log Collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `ping_federate.d/conf.yaml` file to start collecting your PingFederate logs:

    ```yaml
      logs:
        - type: file
          path:  <pf_install>/pingfederate/log/admin.log
          source: ping-federate
          service: admin

        - type: file
          path:  <pf_install>/pingfederate/log/audit.log
          source: ping-federate
          service: audit
    ```

    **NOTE**: Make sure to address the below points.

    1. Change the `<pf_install>` to the location of your PingFederate installation.

    2. The default path of PingFederate's output would be `/pingfederate/log` and `filenames` would be `admin.log` and `audit.log`. If you have changed default path and filename then update the `path` parameter in `conf.yaml` accordingly.


3. [Restart the Agent][2].
### Validation

[Run the Agent's status subcommand][5] and look for `ping-federate` under the Checks section.

## Data Collected

### Logs

The Ping Federate integration collects the following log types.

| Format     | Event Types    |
| ---------  | -------------- |
| CEF | admin, audit|

### Supported Log Formats

#### Admin
Default log format: 

```
<pattern>%d | %X{user} | %X{roles} | %X{ip} | %X{component} | %X{event} | %X{eventdetailid} | %m%n</pattern>
```

#### Audit
Default log format: 

```
<pattern>%d| %X{trackingid}| %X{event}| %X{subject}| %X{ip} | %X{app}| %X{connectionid}| %X{protocol}| %X{host}| %X{role}| %X{status}| %X{adapterid}| %X{description}| %X{responsetime} %n</pattern>
```

Additional field log format: 

```
<pattern>%d| %X{trackingid}| %X{event}| %X{subject}| %X{ip} | %X{app}| %X{connectionid}| %X{protocol}| %X{host}| %X{role}| %X{status}| %X{adapterid}| %X{description}| %X{responsetime}| %X{attrackingid}| %X{attributes}| %X{granttype}| %X{initiator}| %X{inmessagetype}| %X{inresponseto}| %X{localuserid}| %X{requestid}| %X{requeststarttime}| %X{responseid}| %X{stspluginid}| %X{targetsessionid}| %X{authenticationsourceid}| %X{validatorid}| %X{virtualserverid}| %X{connectionname}| %X{httprequestid}%n</pattern>
```


**Note**: Additional fields are supported only if they are configured in above sequence. Also, if any field is not configured, then integration will not support the additional fields.

### Metrics

The Ping Federate does not include any metrics.

### Events

The Ping Federate integration does not include any events.

### Service Checks

The Ping Federate integration does not include any service checks.

## Troubleshooting

If you see a **Permission denied** error while monitoring the log files, give the `dd-agent` user read permission on them.

  ```shell
  sudo chown -R dd-agent:dd-agent <pf_install>/pingfederate/log/admin.log
  sudo chown -R dd-agent:dd-agent <pf_install>/pingfederate/log/audit.log
  ```
## Support

For any further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://docs.pingidentity.com/r/en-us/pingfederate-112/pf_pingfederate_landing_page
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
