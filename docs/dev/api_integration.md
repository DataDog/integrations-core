---
title: Create an API Integration
type: documentation
---

## Overview

Use a [Datadog API endpoint][1] to enrich and submit data from your backend, or pull data directly out of Datadog. API integrations work well in building a connector between Datadog and another SaaS platform. This method is ideal for Technology Partners that are SaaS based, and have an existing website for users to log into for authorization purposes.

API integrations send the following types of data to Datadog:

- [Metrics][2]
- [Logs & Log Pipelines][3]
- [Events][4]
- [Service Checks][5]
- [Traces][6]
- [Incidents][7]
- [Security Events][8]

This page provides instructions for creating an API integration. REMOVE: For more information about why you would want to create an API-based integration, see [Creating your own solution][9]. Since API integrations do not use the Datadog Agent to collect data, you need to create an informational tile-only listing once your development work is complete. 

## Setup

### Prerequisites

- You must have an [API key][10] and [application key][11].
- Determine which [Datadog site][12] you want to use.

An API key is required to submit data to a Datadog API endpoint. An application key is required to query data from Datadog or to create resources within the Datadog site. For more information, see [API and Application Key][13].

Create a connection to Datadog in your company's platform using the API key, application key, and site URL. 

### Create an OAuth client
Instead of requesting these credentials directly from a user, Datadog recommends using an [OAuth client][14] to handle authorization and access for API-based integrations. For more information, see [OAuth for Integrations][15] and [Authorization Endpoints][16]

You can explore examples of existing API integrations in the `integrations-extras` repository such as [Vantage][17].

To create an API integration, click here.[24]

Additional helpful documentation, links, and articles:

- [Using the Datadog API][1]
- [OAuth for Integrations][14]

[1]: https://docs.datadoghq.com/api/latest/using-the-api/
[2]: https://docs.datadoghq.com/api/latest/metrics/
[3]: https://docs.datadoghq.com/logs/faq/partner_log_integration/
[4]: https://docs.datadoghq.com/api/latest/events/
[5]: https://docs.datadoghq.com/api/latest/service-checks/
[6]: https://docs.datadoghq.com/tracing/guide/send_traces_to_agent_by_api/
[7]: https://docs.datadoghq.com/api/latest/incidents/
[8]: https://docs.datadoghq.com/api/latest/security-monitoring/
[9]: https://docs.datadoghq.com/developers/#creating-your-own-solution
[10]: https://docs.datadoghq.com/account_management/api-app-keys/#api-keys
[11]: https://docs.datadoghq.com/account_management/api-app-keys/#application-keys
[12]: https://docs.datadoghq.com/getting_started/site
[13]: https://docs.datadoghq.com/account_management/api-app-keys/
[14]: https://docs.datadoghq.com/developers/authorization/
[15]: https://docs.datadoghq.com/developers/integrations/oauth_for_integrations/
[16]: https://docs.datadoghq.com/developers/authorization/oauth2_endpoints/
[17]: https://github.com/DataDog/integrations-extras/tree/master/vantage
[18]: https://www.python.org/downloads/
[19]: https://pypi.org/project/datadog-checks-dev/
[20]: https://docs.datadoghq.com/developers/integrations/check_references/#manifest-file
[21]: https://github.com/DataDog/integrations-extras/
[22]: https://app.datadoghq.com/integrations
[23]: /developers/integrations/python
[24]: Create a tile link