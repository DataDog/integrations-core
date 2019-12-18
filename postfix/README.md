# Postfix Check

![Postfix Graph][1]

## Overview

This check monitors the size of all your Postfix queues.

## Setup
### Installation

The Postfix check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Postfix servers.

### Configuration

This check can be configured to use the `find` command. This requires granting `sudo` access to the `dd-agent` to get a count of messages in the `incoming`, `active`, and `deferred` mail queues.

Optionally, you can configure the Agent to use a built in `postqueue -p` command to get a count of messages in the `active`, `hold`, and `deferred` mail queues. `postqueue` is executed with set group ID privileges without the need for `sudo`.

**WARNING**: Using `postqueue` to monitor the mail queues doesn't report a count of messages for the `incoming` queue.

#### Metric collection
##### Using sudo

1. Edit the file `postfix.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample postfix.d/conf.yaml][4] for all available configuration options:

    ```yaml
      init_config:
        ## @param postfix_user - string - required
        ## The user running dd-agent must have passwordless sudo access for the find
        ## command to run the postfix check.  Here's an example:
        ## example /etc/sudoers entry:
        ##   dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/incoming -type f
        ##
        ## Redhat/CentOS/Amazon Linux flavours need to add:
        ##          Defaults:dd-agent !requiretty
        #
        postfix_user: postfix

      instances:

          ## @param directory - string - required
          ## Path to the postfix directory.
          #
        - directory: /var/spool/postfix

          ## @param queues - list of string - required
          ## List of queues to monitor.
          #
          queues:
            - incoming
            - active
            - deferred
    ```

2. For each mail queue in `queues`, the Agent forks a `find` on its directory. It uses `sudo` to do this with the privileges of the Postfix user, so you must add the following lines to `/etc/sudoers` for the Agent's user, `dd-agent`, assuming Postfix runs as `postfix`:

    ```
    dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/incoming -type f
    dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/active -type f
    dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/deferred -type f
    ```

3. [Restart the Agent][5]

##### Using postqueue

1. Edit the `postfix.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]:

    ```yaml
      init_config:

        ## @param postqueue - boolean - optional - default: false
        ## Set `postqueue: true` to gather mail queue counts using `postqueue -p`
        ## without the use of sudo. Postqueue binary is ran with set-group ID privileges,
        ## so that it can connect to Postfix daemon processes.
        ## Only `tags` keys are used from `instances` definition.
        ## Postfix has internal access controls that limit activities on the mail queue.
        ## By default, Postfix allows `anyone` to view the queue. On production systems
        ## where the Postfix installation may be configured with stricter access controls,
        ## you may need to grant the dd-agent user access to view the mail queue.
        ##
        ## postconf -e "authorized_mailq_users = dd-agent"
        ##
        ## http://www.postfix.org/postqueue.1.html
        ##
        ## authorized_mailq_users (static:anyone)
        ## List of users who are authorized to view the queue.
        #
        postqueue: true

      instances:

          ## @param config_directory - string - optional
          ## The config_directory option only applies when `postqueue: true`.
          ## The config_directory is the location of the Postfix configuration directory
          ## where main.cf lives.
          #
        - config_directory: /etc/postfix

          ## @param queues - list of string - required
          ## List of queues to monitor.
          #
          queues:
            - incoming
            - active
            - deferred
    ```

2. For each `config_directory` in `instances`, the Agent forks a `postqueue -c` for the Postfix configuration directory. Postfix has internal access controls that limit activities on the mail queue. By default, Postfix allows `anyone` to view the queue. On production systems where the Postfix installation may be configured with stricter access controls, you may need to grant the `dd-agent` user access to view the mail queue ([postqueue Postfix documentation][6]):

    ```
    postconf -e "authorized_mailq_users = dd-agent"
    ```

    List of users who are authorized to view the queue:

    ```
    authorized_mailq_users (static:anyone)
    ```


3. [Restart the Agent][5].

#### Log collection

**Available for Agent >6.0**

Postfix sends logs to the syslog daemon, which then writes logs to the file system. The naming convention and log file destinations are configurable:

```
/etc/syslog.conf:
    mail.err                                    /dev/console
    mail.debug                                  /var/log/mail.log
```

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

2. Add the following configuration block to your `postfix.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample postfix.d/conf.yaml][5] for all available configuration options.

    ```yaml
      logs:
        - type: file
          path: /var/log/mail.log
          source: postfix
          service: myapp
    ```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][7] and look for `postfix` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][8] for a list of metrics provided by this check.

### Events
The Postfix check does not include any events.

### Service Checks
The Postfix check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

* [Monitor Postfix queue performance][10]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/postfix/images/postfixgraph.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/postfix/datadog_checks/postfix/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: http://www.postfix.org/postqueue.1.html
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/postfix/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-postfix-queues
