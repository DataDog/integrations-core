# CoreDNS Integration

## Overview
Get metrics from CoreDNS in real time to visualize and monitor DNS failures and cache hits/misses
## Setup
### Installation
The CoreDNS check is included in the [Datadog Agent](https://app.datadoghq.com/account/settings#agent) package, so you don't need to install anything else on your servers.

### Configuration
Edit the `coredns.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6], to point to your server and port, set the masters to monitor. See the [sample coredns.d/conf.yaml][2] for all available configuration options.

#### Using with service discovery
If you are using 1 dd-agent pod (daemon set) per kubernetes worker nodes, you could use the following annotations on your kube-dns pod to get the data retrieve automatically.

```yaml
metadata:
  annotations:
    ad.datadoghq.com/coredns.check_names: '["coredns"]'
    ad.datadoghq.com/coredns.init_configs: '[{}]'
    ad.datadoghq.com/coredns.instances: '[[{"prometheus_endpoint":"http://%%host%%:9153/metrics", "tags":["dns-pod:%%host%%"]}]]'
```

**Remarks:**

 - Notice the "dns-pod" tag that will keep track of the target dns pod IP. The other tags will be related to the dd-agent that is polling the informations using the service discovery.
 - The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's spec. Do not add it at the outer spec level.


### Validation

[Run the Agent's `status` subcommand][3] and look for `coredns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The CoreDNS check does not include any event at this time.

### Service Checks
The CoreDNS check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][7].

## Development

Please refer to the [main documentation][6]
for more details about how to test and develop Agent based integrations.

[1]: https://raw.githubusercontent.com/DataDog/cookiecutter-datadog-check/master/%7B%7Bcookiecutter.check_name%7D%7D/images/snapshot.png
[2]: https://github.com/DataDog/integrations-core/blob/master/coredns/datadog_checks/coredns/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/cookiecutter-datadog-check/blob/master/%7B%7Bcookiecutter.check_name%7D%7D/metadata.csv
[6]: https://docs.datadoghq.com/developers/
[7]: http://docs.datadoghq.com/help/