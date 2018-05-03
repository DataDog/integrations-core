# Amazon Fargate

## Overview

Amazon Fargate is a technology that provisions containers for your applications. ECS containers provisioned by Fargate are automatically scaled, load balanced, and managed. Fargate schedules your containers for availability, providing an easier way to build and operate containerized applications.

Connect Fargate to Fargate in order to:

* Monitor the health of your tasks and containers in real time.
* Collect metrics from your containerized applications running in Fargate tasks.

## Setup

To enable monitoring of applications deployed in Fargate, you will need to add a Datadog Agent contaienr to your task definitions.
Additional details are available in our [AWS Fargate guide](https://docs.datadoghq.com/integrations/ecs_fargate/).
