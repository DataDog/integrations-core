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

This page walks through how Technology Partners build an out-of-the-box integration using the Datadog Agent or Datadog's API. 

Datadog Technology Partners can publish their out-of-the-box integrations on the Integrations page for customers to access. 
The **Integrations** page includes integrations and Datadog Apps built by both Datadog and our Technology Partners, available at no cost to Datadog customers. 

The [Datadog Marketplace][3] is a commercial platform for Technology Partners to sell a variety of offerings including integrations, Datadog Apps, software subscriptions/licenses, and professional services to Datadog customers.

## Datadog Integrations

[API-based Integration][1]
API-based integrations enrich a customer's Datadog account by submitting data from your platform via the Datadog API. Customers authorize API integrations through OAuth, and partners write and host their own code that make up the integration. API integrations work well for partners building a connector between Datadog and another SaaS platform.

[Agent-based Integration][2]
Agent-based integrations are a full data integration that includes code and uses the Datadog Agent to collect data. Agent integrations are best suited for general use-cases such as application frameworks, open source projects, or commonly used software. Writing an integration requires you to publish and deploy your solution as a Python wheel (.whl)

## Why create an integration?

Out-of-the-box Metrics - Metrics reported from accepted integrations (unless the integration is sending in potentially unlimited metrics) are not counted as custom metrics, and therefore don’t impact a customer's custom metric allocation.

Adoption - Ensuring native support for Datadog reduces friction to adoption and incentivizes Datadog customers to build out their technology stack with partner technologies.

Added Visibility - Partners are featured within the Datadog ecosystem. All integrations are located on the Integraitons page adding visibility. 

{{< whatsnext desc="See the following integration documentation to get started:" >}}
  {{< nextlink href="/developers/integrations/create_a_tile" >}}Create an Integration Tile {{< /nextlink >}}
  {{< nextlink href="/developers/integrations/api_integration" >}}Create an Agent Integration {{< /nextlink >}}
{{< /whatsnext >}}

### Responsibilities
Going forward, you, as the author of the integration, are the active maintainer of the integration. You’re responsible for maintaining the code and ensuring the integration’s functionality. There is no specific time commitment, but you must be a maintainer and take care of the code for the foreseeable future. Datadog extends support on a best-effort basis for partner-built integrations, so please reach out to Datadog support if help is needed.

## Let's Get Started 
To create an API integration, [click here][1].
To create an Agent-based integration, [click here][2].

{{< partial name="whats-next/whats-next.html" >}}

[1]: API Based link
[2]: Agent based link 
[3]: Marketplace link