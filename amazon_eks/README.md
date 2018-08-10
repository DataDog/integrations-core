# Amazon EKS Integration

![EKS Dashboard][1]

## Overview

Elastic Container Service for Kubernetes (EKS) is the latest addition to AWS, a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. Whether you are migrating an existing Kubernetes application to EKS, or are deploying a new cluster, Datadog helps you monitor your EKS environment in real time.

## Setup

Because Datadog already integrates with Kubernetes and AWS, it is ready-made to monitor EKS. If you're running the Agent in a Kubernetes cluster and plan to migrate to EKS, you can continue monitoring your cluster with Datadog. 

### Metric Collection

Monitoring EKS requires that you set up the Datadog integrations for:

* [Kubernetes][2]
* [AWS][3]
* [AWS EC2][4]

along with integrations for any other AWS services you're running with EKS (e.g., [ELB][5])

### Log Collection

**Available for Agent >6.0**

The setup is exactly the same as for Kubernetes. 
To start collecting logs from all your containers, use your Datadog Agent [environment variables][6].

Take also advantage of DaemonSets to [automatically deploy the Datadog Agent on all your nodes][7]. 

Follow the [container log collection steps][8] to learn more about those environment variables and discover more advanced setup options.

## Troubleshooting
Need help? Contact [Datadog Support][9].

## Further Reading

* [Monitor Amazon EKS with Datadog][10]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/amazon_eks/images/amazon_eks_dashboard.png
[2]: https://docs.datadoghq.com/integrations/kubernetes/
[3]: https://docs.datadoghq.com/integrations/amazon_web_services/
[4]: https://docs.datadoghq.com/integrations/amazon_ec2/
[5]: https://docs.datadoghq.com/integrations/amazon_elb/
[6]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#log-collection-setup
[7]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#container-installation
[8]: https://docs.datadoghq.com/logs/log_collection/docker/#option-2-container-installation
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/announcing-eks/
