---
title: Create an API Integration
type: documentation
---

## Overview

Use a [Datadog API endpoint][1] to enrich and submit data from your backend. API integrations work well in building a connector between Datadog and another SaaS platform. Partners will write and host their code within their enviornment.

 This method is ideal for Technology Partners that are SaaS based, and have an existing website for users to log into for authorization purposes.

API integrations send the following types of data to Datadog:

- [Metrics][2]
- [Logs & Log Pipelines][3]
- [Events][4]
- [Service Checks][5]
- [Traces][6]
- [Incidents][7]
- [Security Events][8]

This page provides instructions for creating an API integration.  Since API integrations do not use the Datadog Agent to collect data, you need to create an informational tile-only listing to display your offering on the Integrations page once your development work is complete.
## Setup

### Prerequisites

- You must implement OAuth in order to submit data or pull data out of Datadog. 
- You must support all [Datadog sites][12].

### Create an OAuth client
Instead of requesting API and Application keys directly from a user, Datadog requires using an [OAuth client][14] to handle authorization and access for API-based integrations. For more information, see [OAuth for Integrations][15] and [Authorization Endpoints][16]. 

You can explore examples that use OAuth in the `integrations-extras` repository such as [Vantage][17].

## Development Process

You can expect the following process for building an API-based integration:
1. Meet with the Datadog Technology Partner team to discuss your offering and use cases.
2. Request a sandbox account for development.
3. Begin development of your integration, which will include writing and hosting integration code on your end, as well as implementing the OAuth protocol.
4. Test your integration, as well as your OAuth client, in your sandbox account.
5. Once your development work is tested and complete, **follow the steps to [create a tile] in order to display your offering on the Marketplace or Integrations page**.
6. Once your pull requested is submitted and approved, the team will schedule a demo for a final review of your integration.
7. You'll have the option of testing the tile and integration in your sandbox account before publishing, or immediately publishing the integration for all customers. 

To create an API integration, [click here][24]. 


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