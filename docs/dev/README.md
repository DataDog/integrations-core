---
title: Build an Integration
kind: documentation
description: Learn how to develop and publish an offering on the Integrations page.
aliases:
- /guides/agent_checks/
- /agent/agent_checks
- /developers/agent_checks/
dependencies: "https://github.com/DataDog/integrations-core/blob/alai97/add-marketplace-documentation/docs/dev/README.md"
further_reading:
- link: "/developers/"
  tag: "Documentation"
  text: "Learn how to develop on the Datadog platform"
---

## Overview

This page walks through how Technology Partners can build an out-of-the-box integration using the Datadog Agent or Datadog API. 

The [Integrations page][3] includes integrations and custom dashboard widgets built by both Datadog and our Technology Partners, available at no cost to Datadog customers. 

The [Datadog Marketplace][4], on the other hand, is a commercial platform for Technology Partners to _sell_ a variety of offerings, including integrations, custom dashboard widgets, software subscriptions/licenses, and professional services to Datadog customers.

## Datadog Integrations

### [API-based Integration][1]
API-based integrations can enrich a customer's Datadog environment by submitting data from external technologies via the Datadog API. Customers authorize API integrations access to their accounts through OAuth, and partners write and host the implementation code that makes up the integration. API integrations work well for partners building a connector between Datadog and another SaaS platform.

### [Agent-based Integration][2]
Agent-based integrations use the Datadog Agent to submit data via checks written by the partner. The implementation code for these integrations is hosted by Datadog. Agent integrations are best suited for collecting data from custom systems or applications. Writing an agent integration requires you to publish and deploy your solution as a Python wheel (.whl).

## Why create an integration?

Out-of-the-box Metrics - Metrics reported from official Datadog integrations (unless the integration is sending in potentially unlimited metrics) are not counted as custom metrics, and therefore won't impact a customer's custom metric allocation.

Adoption - Ensuring native support for Datadog reduces friction to adoption and incentivizes Datadog customers to build out their technology stack with partner technologies.

Added Visibility - Partners integrations appear on the Integrations page alongside all Datadog-built integrations, providing key visibility to all of Datadog's customers.

### Responsibilities
Going forward, you, as the author of the integration, are the active maintainer of the integration. You are responsible for maintaining the code and ensuring the integration’s functionality. There is no specific time commitment, but you must be a maintainer of the code for the foreseeable future. Datadog extends support on a best-effort basis for partner-built integrations, so please reach out to Datadog support if help is needed.

## Let's Get Started 
To create an API integration, [click here][1].
To create an Agent-based integration, [click here][2].

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://docs.datadoghq.com/developers/integrations/api_integration/
[2]: https://docs.datadoghq.com/developers/integrations/agent_integration/
[3]: https://docs.datadoghq.com/integrations/
[4]: https://docs.datadoghq.com/developers/integrations/marketplace_offering/