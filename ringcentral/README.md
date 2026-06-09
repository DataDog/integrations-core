# RingCentral

## Overview

[RingCentral][1] is a leading cloud-based communication and collaboration platform for businesses. It offers services such as voice, messaging, and video conferencing, seamlessly integrating with various business applications.

The RingCentral integration collects voice and audit logs, as well as Voice (Analytics) and A2P SMS metrics, and sends them to Datadog for comprehensive analysis.

## Setup

To collect RingCentral logs and metrics, click the **Authorize** button to authenticate using OAuth.

To integrate RingCentral with Datadog, you need a RingCentral account with appropriate permissions to access the RingCentral APIs. The required permissions are:

- Read Call Log
- Read Audit Trail
- Analytics
- A2P SMS

## Data Collected

### Logs

The RingCentral integration collects and forwards Voice and Audit logs to Datadog.

### Metrics

The RingCentral integration collects and forwards Voice(Analytics) and SMS metrics to Datadog.

{{< get-metrics-from-git "ringcentral" >}}

### Events

The RingCentral integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.ringcentral.com/
[2]: https://docs.datadoghq.com/help/
