# Varnish Integration

## Overview

Connect Varnish to Datadog in order to:

* Visualize your cache performance in real-time
* Correlate the performance of Varnish with the rest of your applications

## Installation

Install the `dd-check-varnish` package manually or with your favorite configuration manager

## Configuration

Configure the Agent to connect to Varnish

 - Edit conf.d/varnish.yaml
```
init_config:

instances:
    - varnishstat: /usr/bin/varnishstat
      tags:
          - instance:production
```

 - If you're running Varnish 4.1+, you must add the dd-agent user to the varnish group.
```
sudo usermod -a -G varnish dd-agent
```

 - If you want the check to use `varnishadm` and send a service check, the agent must be able to access `varnishadm` with root privileges. For this, you can update your `/etc/sudoers` file with for example:
 ```
 dd-agent ALL=(ALL) NOPASSWD:/usr/bin/varnishadm
 ```



## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        varnish
        -------
          - instance #0 [OK]
          - Collected 8 metrics & 0 events

## Compatibility

The Varnish check is compatible with all major platforms

## Further Reading

To get a better idea of how (or why) to monitor Varnish with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/top-varnish-performance-metrics/) about it.
