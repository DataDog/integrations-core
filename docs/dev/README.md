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

This page walks through how Technology Partners building an out-of-the-box integration using the Agent or Datadog's API. 

Datadog Technology Partners can publish their out-of-the-box integrations on the Integrations page for customers to access. 
The **Integrations** page includes Agent-based or API-based integrations and Datadog Apps built by Datadog and Technology Partners at no cost. 

Whereas the **Marketplace** page is a commercial platform for Datadog customers and Technology Partners to buy and sell a variety of offerings including Agent-based or API-based integrations, Datadog Apps, software subscriptions/licenses, and professional services.

## Datadog Integrations

[API-based Integration][1]
This is to enrich and submit data from your backend. API integrations work well in building a connector between Datadog and another SaaS platform. Partners will write and host their code within their enviornment.

[Agent-based Integration][2]
A full data integration that includes code and uses the Datadog Agent to collect data. 

## Why create an integration?

Out-of-the-box Metrics - Metrics reported from accepted integrations are not counted as custom metrics, and therefore don’t impact your custom metric allocation. (Integrations that emit potentially unlimited metrics may still be considered custom.) 

Adoption - Ensuring native support for Datadog reduces friction to adoption, and incentivizes people to use your product, service, or project. 

Added Visibility - Partners are featured within the Datadog ecosystem. 

{{< whatsnext desc="See the following integration documentation to get started:" >}}
  {{< nextlink href="/developers/integrations/create_a_tile" >}}Create an Integration Tile {{< /nextlink >}}
  {{< nextlink href="/developers/integrations/api_integration" >}}Create an Agent Integration {{< /nextlink >}}
{{< /whatsnext >}}

### Responsibilities
Going forward, you, as the author of the code, are the active maintainer of the integration. You’re responsible for maintaining the code and ensuring the integration’s functionality. There is no specific time commitment, but you must be a maintainer and take care of the code for the foreseeable future. Datadog extends support on a best-effort basis for Extras, so you are not alone.

## Let's Get Started 
To create an API integration, [click here][1].
To create an Agent-based integration, [click here][2].

{{< partial name="whats-next/whats-next.html" >}}

[1]: API Based link
[2]: Agent based link 