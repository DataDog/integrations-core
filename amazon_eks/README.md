![EKS Dashboard](https://raw.githubusercontent.com/DataDog/integrations-core/a30e284214e465844d18b7ac06c7c2b1dab8b43a/amazon_eks/images/eks_screenboard.png)

## Overview

Elastic Container Service for Kubernetes (EKS) is the latest addition to AWS, a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. Whether you are migrating an existing Kubernetes application to EKS, or are deploying a new cluster, Datadog helps you monitor your EKS environment in real time.

## Setup

Because Datadog already integrates with Kubernetes and AWS, it is ready-made to monitor EKS. If you're running the Agent in a Kubernetes cluster and plan to migrate to EKS, you can continue monitoring your cluster with Datadog. 

Monitoring EKS requires that you set up the Datadog integrations for:

* [Kubernetes](https://docs.datadoghq.com/integrations/kubernetes/)
* [AWS](https://docs.datadoghq.com/integrations/amazon_web_services/)
* [AWS EC2](https://docs.datadoghq.com/integrations/amazon_ec2/)

along with integrations for any other AWS services you're running with EKS (e.g., [ELB](https://docs.datadoghq.com/integrations/amazon_elb/))

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}
