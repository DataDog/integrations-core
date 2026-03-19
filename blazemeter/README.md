# BlazeMeter

## Overview

[BlazeMeter][1] is a cloud-based performance testing platform that enables scalable load testing for web applications, mobile apps, and APIs. It offers a range of testing capabilities, including performance testing and functional testing.

Integrate BlazeMeter with Datadog to gain insights into performance and functional test results metrics data.

## Setup

### Generate API Key Id and API Key Secret in BlazeMeter

1. Log in to [BlazeMeter Account][2].
2. Navigate to the Settings page by clicking the gear icon in the upper-right corner of the page.
3. In the left side bar, under the **Personal** section, click **API Keys**. 
4. Create a new API Key by clicking **+ icon**.
5. In the **Generate API Key** section, enter a name and select an expiration date.
6. Click the **Generate** button to generate the **API Key Id** and **API Key Secret**.

### Connect your BlazeMeter account to Datadog

1. Add your API Key Id and API Key Secret   
    |Parameters|Description|
    |--------------------|--------------------|
    |API Key Id|API Key Id of BlazeMeter Account.|
    |API Key Secret|API Key Secret of BlazeMeter Account.|

2. Click the **Save** button to save your settings.


## Data Collected

### Metrics

See [metadata.csv][3] for a list of metrics provided by this integration.

### Service Checks

The BlazeMeter integration does not include any service checks.

### Events

The BlazeMeter integration does not include any events.

## Support

Need help? Contact [Datadog support][4].

[1]: https://www.blazemeter.com/
[2]: https://auth.blazemeter.com/auth/realms/blazect/protocol/saml/clients/blazemeter
[3]: https://github.com/DataDog/integrations-core/blob/master/blazemeter/metadata.csv
[4]: https://docs.datadoghq.com/help/
