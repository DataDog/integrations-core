# Tanzu Kubernetes Grid Integrated Integration

## Overview

This integration monitors [Tanzu Kubernetes Grid Integrated][1] clusters.

## Setup

Since Datadog already integrates with Kubernetes, it is ready-made to monitor TKGI.

### Kubernetes compute plane

Monitoring Kubernetes compute plane on TKGI requires that you set up the Datadog integration for [Kubernetes][2].

### Kubernetes control plane

Monitoring Kubernetes control plane on TKGI requires the following setup.

#### Upload the BOSH agent release

1. Navigate to https://bosh.io/releases/github.com/DataDog/datadog-agent-boshrelease
2. Select the latest version, copy the `bosh upload-release` command and run it to upload the release to your TKGI environment

#### Configure Kubernetes control plane integrations

Here is the minimal bosh runtime configuration needed to install the agent on the control plane, and configure the integrations:

```
addons:
- include:
    jobs:
    - name: kube-scheduler
      release: kubo
  name: dd-agent
  jobs:
  - name: dd-agent
    release: datadog-agent
    properties:
      dd:
        api_key: <API_KEY>
        integrations:
          etcd:
            init_config: {}
            instances:
            - prometheus_url: https://localhost:2379/metrics
              tls_verify: false
              tls_cert: /var/vcap/jobs/etcd/config/etcd.crt
              tls_private_key: /var/vcap/jobs/etcd/config/etcd.key
          kube_apiserver_metrics:
            init_config: {}
            instances:
            - prometheus_url: http://localhost:8080/metrics
              bearer_token_auth: false
          kube_controller_manager:
            init_config: {}
            instances:
            - prometheus_url: http://localhost:10252/metrics
              leader_election: false
          kube_scheduler:
            init_config: {}
            instances:
            - prometheus_url: http://localhost:10251/metrics
              leader_election: false
releases:
- name: datadog-agent
  version: <BOSH_AGENT_VERSION>
```

The only two things that need to be added here are the API key for Datadog, as well as the BOSH agent version uploaded in the environment (`<API_KEY>` and `<BOSH_AGENT_VERSION>`).

For more information about all the available properties, see:
https://bosh.io/jobs/dd-agent?source=github.com/DataDog/datadog-agent-boshrelease

Upload the sample configuration above, by saving it to a file and running:
```
bosh update-config --type runtime --name datadog-agent <PATH_TO_FILE>
```

#### Redeploy TKGI Tile

Once the release and the configuration have been uploaded, redeploy the TKGI tile in the Ops Manager (making sure the “upgrade clusters” errand is checked) in order to pick up the runtime configuration and install the agent on the master VM of the Kubernetes cluster.

### Metric collection

The Datadog Agent collects your typical [Kubernetes integrations metrics][2].

### Log collection

_Available for Agent versions >6.0_

The setup is exactly the same as for Kubernetes.
To start collecting logs from all your containers, use your Datadog Agent [environment variables][3].

You can also take advantage of DaemonSets to [automatically deploy the Datadog Agent on all your nodes][4].

Follow the [container log collection steps][5] to learn more about those environment variables and discover more advanced setup options.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid-Integrated-Edition/index.html
[2]: https://docs.datadoghq.com/integrations/kubernetes/
[3]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#log-collection-setup
[4]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#container-installation
[5]: https://docs.datadoghq.com/logs/log_collection/docker/#option-2-container-installation
[6]: https://docs.datadoghq.com/help/
