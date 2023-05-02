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

## Join the Datadog partner network

Before listing an integration on Datadog, you will first need to apply to the [Datadog Partner Network's][5] **Technology Partner** track. Once your application has been approved, you can begin to develop your integration.

## Why create an integration?

**Correlate your data with user observability data** - Leverage Datadog to increase the value of your platform by  allowing customers to see the data from your platform alongside the rest of their technology stack.

**Increase mean-time-to-resolution (MTTR) for customers** - When a customer's account is enriched with data from an integration, they are able to see a broader view of their entire stack, allowing them to debug and remediate issues more quickly. 

**Increase adoption and visibility** - Ensuring native functionality for Datadog reduces friction to adoption, and displaying a tile on our Integrations page provides key visibility to all of Datadog's customers.

**Submit out-of-the-box metrics at no extra cost** - Metrics reported from official Datadog integrations (unless the integration is sending in potentially unlimited metrics) are not counted as custom metrics, and therefore won't impact a customer's billing through custom metric allocation.

## Datadog integrations

### [Agent-based Integration][2]
Agent-based integrations use the Datadog Agent to submit data via checks written by the partner. The implementation code for these integrations is hosted by Datadog. Agent Integrations are best suited for collecting data from systems or applications that live in a local area network (LAN) or virtual private cloud (VPC). Writing an Agent integration requires you to publish and deploy your solution as a Python wheel (.whl).

### [API-based Integration][1]
API-based integrations can submit telemetry, such as metrics, traces, logs, and more, from external platforms via the Datadog API. Customers can then visualize and correlate this data alongside data from the rest of their stack, allowing them to quickly analyze and remediate issues. API-based integrations may also read data out of Datadog, once authorized for access by customers via OAuth. Partners write and host the implementation code that makes up the integration. API integrations work well for partners building a connector between Datadog and another SaaS platform.

### Responsibilities
As the author of the integration, you are responsible for maintaining the code and ensuring the integration functions properly across Datadog's regions. Please reach out to Datadog's Support team if help is needed.

## Get started 

### Request a sandbox account

All Technology Partners can request a dedicated sandbox Datadog account to aid in their development. This sandbox account has a free license that you can use to send in data, build out dashboards, and more. 

To request a sandbox account:

1. Log into the [Datadog Partner Portal][5].
2. On your personal homepage, click on the **Learn More** button under **Sandbox Access**.
3. Select **Request Sandbox Upgrade**.

<div class="alert alert-info">If you are already a member of a Datadog organization (including a trial org), you may need to switch to your newly created sandbox. For more information, see the <a href="https://docs.datadoghq.com/account_management/org_switching/">Account Management documentation</a>.</div>

Creating a developer sandbox may take up to one or two business days. Once your sandbox is created, you can [invite new members from your organization][6] to collaborate with.

### Explore learning resources

Once you've joined the Technology Partner track and requested a sandbox account, you can start learning about developing offerings by:

* Completing the on-demand [**Introduction to Datadog Integrations**][7] course on the [Datadog Learning Center][8].
* Reading the documentation about setting up an [OAuth 2.0 client][9] for API-based integrations.

### Build your integration

To create an Agent-based integration, [click here][2].

To create an API integration, [click here][1].

To sell an integration on the Datadog Marketplace, [click here][4].





{{< partial name="whats-next/whats-next.html" >}}

[1]: https://docs.datadoghq.com/developers/integrations/api_integration/
[2]: https://docs.datadoghq.com/developers/integrations/agent_integration/
[3]: https://docs.datadoghq.com/integrations/
[4]: https://docs.datadoghq.com/developers/integrations/marketplace_offering/
[5]: https://partners.datadoghq.com/
[6]: /account_management/users/#add-new-members-and-manage-invites
[7]: https://learn.datadoghq.com/courses/intro-to-integrations
[8]: https://learn.datadoghq.com/
[9]: https://docs.datadoghq.com/developers/authorization/