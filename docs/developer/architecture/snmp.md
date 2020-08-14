# SNMP

!!! note
    This section is meant for developers that want to understand the working of the SNMP integration.

    Be sure you are familiar with [SNMP concepts](../../tutorials/snmp/introduction/), and you have read through the official [SNMP integration docs](https://docs.datadoghq.com/integrations/snmp).

## Overview

While most integrations are either Python, JMX, or implemented in the Agent in Go, the SNMP integration is a bit more complex.

Here's an overview of what this integration entails:

* A [Python check](https://github.com/DataDog/datadog-agent/blob/master/snmp), responsible for:
    * Collecting metrics from a specific device IP.
    * Auto-discovering devices over a network. (Pending deprecation in favor of Agent auto-discovery.)
* An [Agent service listener](https://github.com/DataDog/datadog-agent/blob/master/pkg/autodiscovery/listeners/snmp.go), responsible for auto-discovering devices over a network and forwarding discovered instances to the existing Agent check scheduling pipeline. Also known as "Agent SNMP auto-discovery".

As a diagram:

![](/assets/images/snmp-architecture.png)

## Python Check

### Dependencies

The Python check uses [PySNMP](https://github.com/etingof/pysnmp) to make SNMP queries and manipulate SNMP data (OIDs, variables, and MIBs).

### Device Monitoring

The primary functionality of the Python check is to collect metrics from a given device given its IP address.

As all Python checks, it supports multi-instances configuration, where each instance represents a device:

```yaml
instances:
  - ip_address: "192.168.0.12"
    # <Options...>
```

### Python Auto-Discovery

#### Approach

The Python check includes a multithreaded implementation of device auto-discovery. It runs on instances that use `network_address` instead of `ip_address`:

```yaml
instances:
  - network_address: "192.168.0.0/28"
    # <Options...>
```

Auto-discovery runs a loop in a separate thread that polls each IP in the `network_address` CIDR range for the device `sysObjectID`. If the `sysObjectID` matches one of the registered profiles, the device is added to a set of discovered instances, and will be checked in the next check run. On each check run, a check is run for each discovered device. This is performed in parallel using a thread pool.

#### Caveats

The approach described above is not ideal for several reasons:

* The check code is harder to understand since the two distinct paths ("single device" vs "entire network") live in a single integration.
* Each network instance manages several long-running threads that span well beyond the lifespan of a single check run.
* Each network check pseudo-schedules other instances, which is normally the responsibility of the Agent.

For this reason, auto-discovery was eventually implemented in the Agent as a proper service listener (see below), and users should be discouraged from using Python auto-discovery. When the deprecation period expires, we will be able to remove auto-discovery logic from the Python check, making it exclusively focused on checking single devices.

## Agent Auto-Discovery

### Dependencies

Agent auto-discovery uses [GoSNMP](https://github.com/soniah/gosnmp) to get the `sysObjectID` of devices in the network.

### Approach

Agent auto-discovery implements the same logic than the Python auto-discovery, but as a service listener in the Agent Go package.

This approach leverages the existing Agent scheduling logic, and makes it possible to use device auto-discovery in containerized environments.

Pending official documentation, here is an example configuration:

```yaml
# datadog.yaml

snmp_listener:
  configs:
    - network: 10.0.0.0/28
      version: 2
      community: public
    - network: 10.0.1.0/30
      version: 3
      authentication_protocol: SHA
      authentication_key: "*****"
      privacy_protocol: AES
      privacy_key: "*****"
      ignored_ip_addresses:
        - 10.0.1.0
        - 10.0.1.1
```

### Cluster Agent Integration

For Kubernetes environments, the [Cluster Agent](https://docs.datadoghq.com/agent/cluster_agent/) can be configured to use the Agent auto-discovery logic as a source of [Cluster checks](https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/).

> TODO: example setup, affected files and repos, local testing tools, etc.
