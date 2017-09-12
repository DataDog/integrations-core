# Cacti Integration

## Overview

Get metrics from cacti service in real time to:

* Visualize and monitor cacti states
* Be notified about cacti failovers and events.

## Setup
### Installation

The Cacti check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Cacti servers.

### Configuration

Create a datadog user with read-only rights to the Cacti database

```
sudo mysql -e "create user 'datadog'@'localhost' identified by '<password>';"
sudo mysql -e "grant select on cacti.* to 'datadog'@'localhost';"
```

Check user and rights

```
mysql -u datadog --password=<password> -e "show status" | \
grep Uptime && echo -e "\033[0;32mMySQL user - OK\033[0m" || \
echo -e "\033[0;31mCannot connect to MySQL\033[0m"

mysql -u datadog --password=<password> -D cacti -e "select * from data_template_data limit 1" && \
echo -e "\033[0;32mMySQL grant - OK\033[0m" || \
echo -e "\033[0;31mMissing SELECT grant\033[0m"
```

Configure the Agent to connect to MySQL
Edit conf.d/cacti.yaml

```
init_config:

instances:
    -   mysql_host: localhost
        mysql_user: datadog
        mysql_password: hx3beOpMFcvxn9gXcs0MU3jX
        rrd_path: /path/to/cacti/rra
        #field_names:
        #    - ifName
        #    - dskDevice
        #    - ifIndex
        #rrd_whitelist: /path/to/rrd_whitelist.txt
```

Give the dd-agent user access to the RRD files

```
sudo gpasswd -a dd-agent www-data
sudo chmod -R g+rx /var/lib/cacti/rra/
sudo su - dd-agent -c 'if [ -r /var/lib/cacti/rra/ ];
then echo -e "\033[0;31mdd-agent can read the RRD files\033[0m";
else echo -e "\033[0;31mdd-agent can not read the RRD files\033[0m";
fi'
```

### Validation

Run the Agent's `info` subcommand and look for `cacti` under the Checks section:

```
  Checks
  ======
    [...]

    cacti
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Cacti check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/cacti/metadata.csv) for a list of metrics provided by this integration.

### Events
The Cacti check does not include any event at this time.

### Service Checks
The Cacti check does not include any service check at this time.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)