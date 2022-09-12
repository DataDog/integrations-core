# Amazon EKS Anywhere Integration

![EKS Dashboard][1]

## Overview

Amazon Elastic Kubernetes Service (EKS) is a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. Whether you are migrating an existing Kubernetes application to Amazon EKS, or deploying a new cluster on Amazon EKS on AWS Outposts, Datadog helps you monitor your EKS environments in real time.

[Amazon EKS Anywhere][15] is a deployment option that enables you to create and operate Kubernetes clusters on-premises, including virtual machines (for example, VMware vSphere) and bare metal servers.

## Setup

Because Datadog already integrates with Kubernetes and AWS, it is ready-made to monitor EKS. If you're running the Agent in a Kubernetes cluster and plan to migrate to EKS, you can continue monitoring your cluster with Datadog. 

Additionally, [Amazon EKS Managed Node Groups][2] and [Amazon EKS on AWS Outposts][3] are supported.

### Datadog Helm chart configuration

Use the [Agent deployment instructions with Helm][16] with these additional configuration instructions:

1. Set `datadog.kubelet.tlsVerify` to `false`.
2. Set a toleration on the Agent pod. This is necessary for monitoring the control plane.

The following Helm snippet demonstrates the specific changes for monitoring EKS Anywhere:

```yaml
datadog:
  kubelet:
    tlsVerify: false
agents:
  tolerations:
  - effect: NoSchedule
    key: node-role.kubernetes.io/master
    operator: Exists
```

### Metric collection

Monitoring EKS requires setting up one of the following Datadog integrations along with integrations for any other AWS services you're running with EKS, such as [ELB][7].

- [Kubernetes][4]
- [AWS][5]
- [AWS EC2][6]

### Log collection

_Available for Agent versions >6.0_

The setup is exactly the same as for Kubernetes.
To start collecting logs from all your containers, use your Datadog Agent [environment variables][8].

Use DaemonSets to [automatically deploy the Datadog Agent on all of your nodes][9].

Follow the [container log collection instructions][10] to learn more about environment variables and advanced setup options.

## Troubleshooting

Need help? Contact [Datadog support][11].

## Further Reading

- [Monitor Amazon EKS with Datadog][12]
- [Key metrics for Amazon EKS monitoring][13]
- [Amazon EKS on AWS Fargate][14]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/amazon_eks/images/amazon_eks_dashboard.png
[2]: https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
[3]: https://docs.aws.amazon.com/eks/latest/userguide/eks-on-outposts.html
[4]: https://docs.datadoghq.com/integrations/kubernetes/
[5]: https://docs.datadoghq.com/integrations/amazon_web_services/
[6]: https://docs.datadoghq.com/integrations/amazon_ec2/
[7]: https://docs.datadoghq.com/integrations/amazon_elb/
[8]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#log-collection-setup
[9]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#container-installation
[10]: https://docs.datadoghq.com/logs/log_collection/docker/#option-2-container-installation
[11]: https://docs.datadoghq.com/help/
[12]: https://www.datadoghq.com/blog/announcing-eks
[13]: https://www.datadoghq.com/blog/eks-cluster-metrics
[14]: https://docs.datadoghq.com/integrations/eks_fargate/
[15]: https://aws.amazon.com/eks/eks-anywhere/
[16]: https://docs.datadoghq.com/agent/kubernetes/?tab=helm#installation
