# Datadog Blueprints Add-On for Amazon EKS Blueprints

## Overview

Amazon Elastic Kubernetes Service (EKS) is a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. 

Amazon EKS Blueprints is a framework that consolidates cluster configuration and deployment tools.

The Datadog Blueprints add-on uses Blueprints to deploy the Datadog Agent on Amazon EKS.

## Setup

### Installation

```
npm install @datadog/datadog-eks-blueprints-addon
```

### Usage

#### Using an existing Kubernetes secret

```js
import * as cdk from 'aws-cdk-lib';
import * as blueprints from '@aws-quickstart/eks-blueprints';
import { DatadogAddOn } from '@datadog/datadog-eks-blueprints-addon';
const app = new cdk.App();
const addOns: Array<blueprints.ClusterAddOn> = [
    new DatadogAddOn({
        // Kubernetes secret holding Datadog API key
        // The value should be set with the `api-key` key in the secret object.
        apiKeyExistingSecret: '<secret name>'
    })
];
const account = '<aws account id>'
const region = '<aws region>'
const props = { env: { account, region } }
new blueprints.EksBlueprint(app, { id: '<eks cluster name>', addOns}, props)
```

#### Using AWS Secrets Manager
Store your Datadog API key using AWS Secrets Manager:

```
aws secretsmanager create-secret --name <secret name> --secret-string <api_key> --region <aws region>
```

Refer to the previously created secret with `apiKeyAWSSecret`.

```js
import * as cdk from 'aws-cdk-lib';
import * as blueprints from '@aws-quickstart/eks-blueprints';
import { DatadogAddOn } from '@datadog/datadog-eks-blueprints-addon';
const app = new cdk.App();
const addOns: Array<blueprints.ClusterAddOn> = [
    new DatadogAddOn({
        apiKeyAWSSecret: '<secret name>'
    })
];
const account = '<aws account id>'
const region = '<aws region>'
const props = { env: { account, region } }
new blueprints.EksBlueprint(app, { id: '<eks cluster name>', addOns}, props)
```

### Configuation

#### Options

| Option                  |Description                                          | Default                       |
|-------------------------|-----------------------------------------------------|-------------------------------|
| `apiKey`                | Your Datadog API key                                | ""                            |
| `appKey`                | Your Datadog app key                                | ""                            |
| `apiKeyExistingSecret`  | Existing Kubernetes Secret storing the API key      | ""                            |
| `appKeyExistingSecret`  | Existing Kubernetes Secret storing the app key      | ""                            |
| `apiKeyAWSSecret`       | Secret in AWS Secrets Manager storing the API key   | ""                            |
| `appKeyAWSSecret`       | Secret in AWS Secrets Manager storing the app key   | ""                            |
| `namespace`             | Namespace to install the Datadog Agent              | "default"                     |
| `version`               | Version of the Datadog Helm chart                   | "2.28.13"                     |
| `release`               | Name of the Helm release                            | "datadog"                     |
| `repository`            | Repository of the Helm chart                        | "https://helm.datadoghq.com"  |
| `values`                | Configuration values passed to the chart. [See options][2]. | {}                            |


See the [Datadog Helm chart][2] for all Agent configuration options. You can then pass these values using the `values` option.

### Metric collection

Monitoring EKS requires that you set up one of the following Datadog integrations:

- [Kubernetes][4]
- [AWS][5]
- [AWS EC2][6]

Also set up the integrations for any other AWS services that you are running with EKS, such as [ELB][3].

## Data Collected


## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://github.com/DataDog/helm-charts/tree/main/charts/datadog#all-configuration-options
[3]: https://docs.datadoghq.com/integrations/amazon_elb/
[4]: https://docs.datadoghq.com/integrations/kubernetes/
[5]: https://docs.datadoghq.com/integrations/amazon_web_services/
[6]: https://docs.datadoghq.com/integrations/amazon_ec2/