# Openstack Integration

## Overview

Get metrics from openstack service in real time to:

* Visualize and monitor openstack states
* Be notified about openstack failovers and events.

## Setup
### Installation

Install the `dd-check-openstack` package manually or with your favorite configuration manager

### Configuration

Edit the `openstack.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        openstack
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The openstack check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/openstack/metadata.csv) for a list of metrics provided by this integration.

### Events
The Openstack check does not include any event at this time.

### Service Checks
The Openstack check does not include any service check at this time.

## Further Reading
### Blog Article
To get a better idea of how (or why) to integrate your Nova OpenStack compute module with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/openstack-monitoring-nova/) about it.

See also our blog posts: 
* [Install OpenStack in two commands for dev and test](https://www.datadoghq.com/blog/install-openstack-in-two-commands/)
* [OpenStack: host aggregates, flavors, and availability zones](https://www.datadoghq.com/blog/openstack-host-aggregates-flavors-availability-zones/)
