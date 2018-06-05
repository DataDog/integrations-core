---
display_name: Amazon EKS
doc_link: https://docs.datadoghq.com/integrations/amazon_eks/
has_logo: true
integration_title: Amazon EKS
is_public: true
kind: integration
name: amazon_eks
public_title: Datadog-Amazon EKS Integration
categories:
- aws
- containers
- orchestration
further_reading:
- link: "graphing/infrastructure/livecontainers"
  text: List and explore all containers in your EKS cluster
- link: "graphing/infrastructure/process"
  text: Understand what is going on at any level of your system
---


![EKS Dashboard](https://raw.githubusercontent.com/DataDog/integrations-core/a30e284214e465844d18b7ac06c7c2b1dab8b43a/amazon_eks/images/eks_screenboard.png)

## Overview

Elastic Container Service for Kubernetes (EKS) is the latest addition to AWS, a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. Whether you are migrating an existing Kubernetes application to EKS, or are deploying a new cluster, Datadog helps you monitor your EKS environment in real time.

## Setup

Because Datadog already integrates with Kubernetes and AWS, it is ready-made to monitor EKS. If you're running the Agent in a Kubernetes cluster and plan to migrate to EKS, you can continue monitoring your cluster with Datadog. 

Monitoring EKS requires that you set up the Datadog integrations for:

* [Kubernetes][1]
* [AWS][2]
* [AWS EC2][3]

along with integrations for any other AWS services you're running with EKS (e.g., [ELB][4]).

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: /integrations/kubernetes
[2]: /integrations/amazon_web_services
[3]: /integrations/amazon_ec2
[4]: /integrations/amazon_elb