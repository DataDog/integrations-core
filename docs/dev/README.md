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

The [Integrations page][3] includes integrations built by both Datadog and our Technology Partners, available at no cost to Datadog customers. 

The [Datadog Marketplace][4], on the other hand, is a commercial platform for Technology Partners to _sell_ a variety of offerings, including integrations, software licenses, and professional services to Datadog customers.

## Datadog Integrations

### [Agent-based Integration][2]
Agent-based integrations use the Datadog Agent to submit data via checks written by the partner. The implementation code for these integrations is hosted by Datadog. Agent Integrations are best suited for collecting data from systems or applications that live in a local area network (LAN) or virtual private cloud (VPC). Writing an Agent integration requires you to publish and deploy your solution as a Python wheel (.whl).

### [API-based Integration][1]
API-based integrations can enrich a customer's Datadog environment by submitting data from external technologies via the Datadog API. Customers authorize API integrations access to their accounts through OAuth, and partners write and host the implementation code that makes up the integration. API integrations work well for partners building a connector between Datadog and another SaaS platform.

## Why create an integration?

**Correlate your data with user observability data** - Leverage Datadog to increase the value of your platform by  allowing customers to see the data from your platform alongside the rest of their technology stack.

**Increase MTTR for customers** - When a customer's account is enriched with data from an integration, they are able to see a broader view of their entire stack, allowing them to debug and remediate issues more quickly. 

**Increase Adoption and Visibility** - Ensuring native support for Datadog reduces friction to adoption, and displaying a tile on our Integrations page provides key visibility to all of Datadog's customers.

**Submit out-of-the-box metrics at no extra cost** - Metrics reported from official Datadog integrations (unless the integration is sending in potentially unlimited metrics) are not counted as custom metrics, and therefore won't impact a customer's custom metric allocation.

### Responsibilities
Going forward, you, as the author of the integration, are the active maintainer of the integration. You are responsible for maintaining the code and ensuring the integration’s functionality. Datadog extends support on a best-effort basis for partner-built integrations, so please reach out to Datadog support if help is needed.

## Join the Datadog partner network

Before listing an integration on Datadog, you will first need to apply to the [Datadog Partner Network's][3] **Technology Partner** track. Once your application has been approved, you can begin to develop your integration.

## Request a sandbox account

All Technology Partners can request a dedicated sandbox Datadog account to aid in their development. This sandbox account has a free license that you can use to send in data, build out dashboards, and more. 

To request a sandbox account:

1. Log into the [Datadog Partner Portal][6].
2. On your personal homepage, click on the **Learn More** button under **Sandbox Access**.
3. Select **Request Sandbox Upgrade**.

<div class="alert alert-info">If you are already a member of a Datadog organization (including a trial org), you may need to switch to your newly created sandbox. For more information, see the <a href="https://docs.datadoghq.com/account_management/org_switching/">Account Management documentation</a>.</div>

Creating a developer sandbox may take up to one or two business days. Once your sandbox is created, you can [invite new members from your organization][7] to collaborate with.

## Let's Get Started 
To create an Agent-based integration, [click here][2].

To create an API integration, [click here][1].

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://docs.datadoghq.com/developers/integrations/api_integration/
[2]: https://docs.datadoghq.com/developers/integrations/agent_integration/
[3]: https://docs.datadoghq.com/integrations/
[4]: https://docs.datadoghq.com/developers/integrations/marketplace_offering/