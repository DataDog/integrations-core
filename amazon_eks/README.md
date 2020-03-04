# Amazon EKS Integration

![EKS Dashboard][1]

## Overview

Elastic Container Service for Kubernetes (EKS) is the latest addition to AWS, a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. Whether you are migrating an existing Kubernetes application to EKS, or are deploying a new cluster, Datadog helps you monitor your EKS environment in real time.

## Setup

Because Datadog already integrates with Kubernetes and AWS, it is ready-made to monitor EKS. If you're running the Agent in a Kubernetes cluster and plan to migrate to EKS, you can continue monitoring your cluster with Datadog. [AWS EKS Managed Node Groups][2] are also supported.

### Metric collection

Monitoring EKS requires that you set up the Datadog integrations for:

- [Kubernetes][3]
- [AWS][4]
- [AWS EC2][5]

along with integrations for any other AWS services you're running with EKS (e.g., [ELB][6])

### Log collection

_Available for Agent versions >6.0_

The setup is exactly the same as for Kubernetes.
To start collecting logs from all your containers, use your Datadog Agent [environment variables][7].

Take also advantage of DaemonSets to [automatically deploy the Datadog Agent on all your nodes][8].

Follow the [container log collection steps][9] to learn more about those environment variables and discover more advanced setup options.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

- [Monitor Amazon EKS with Datadog][11]
- [Key metrics for Amazon EKS monitoring][12]
- [Amazon EKS on AWS Fargate][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/amazon_eks/images/amazon_eks_dashboard.png
[2]: https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
[3]: https://docs.datadoghq.com/integrations/kubernetes
[4]: https://docs.datadoghq.com/integrations/amazon_web_services
[5]: https://docs.datadoghq.com/integrations/amazon_ec2
[6]: https://docs.datadoghq.com/integrations/amazon_elb
[7]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#log-collection-setup
[8]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#container-installation
[9]: https://docs.datadoghq.com/logs/log_collection/docker/#option-2-container-installation
[10]: https://docs.datadoghq.com/help
[11]: https://www.datadoghq.com/blog/announcing-eks
[12]: https://www.datadoghq.com/blog/eks-cluster-metrics
[13]: https://docs.datadoghq.com/integrations/amazon_eks_fargate/
