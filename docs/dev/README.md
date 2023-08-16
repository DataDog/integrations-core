---
title: Build an Integration
kind: documentation
description: Learn how to develop and publish an offering on the Integrations page.
aliases:
- /guides/agent_checks/
- /agent/agent_checks
- /developers/agent_checks/
further_reading:
- link: "/developers/integrations/agent_integration/"
  tag: "Documentation"
  text: "Create an Agent integration"
- link: "/developers/integrations/api_integration/"
  tag: "Documentation"
  text: "Create an API integration"
- link: "/developers/integrations/marketplace_offering/"
  tag: "Documentation"
  text: "Learn how to sell an integration on the Datadog Marketplace"
- link: "/developers/"
  tag: "Documentation"
  text: "Learn how to develop on the Datadog platform"
---

## Overview

This page walks you through how Technology Partners can [build an integration](#create-a-datadog-integration) using the [Datadog Agent][11] or the [Datadog API][12], and list their offering on the **Integrations** or **Marketplace** page. 

{{< tabs >}}
{{% tab "Integrations" %}}

The [Integrations page][101] includes integrations built by both Datadog and our Technology Partners, available at _no cost_ to Datadog customers. 

{{< img src="developers/integrations/integrations_overview.png" alt="The Datadog Integrations page" style="width:100%;" >}}

[101]: https://app.datadoghq.com/integrations

{{% /tab %}}
{{% tab "Marketplace" %}}

The [Marketplace page][101] is a commercial platform for Technology Partners to _sell_ a variety of offerings, including integrations, software licenses, and professional services to Datadog customers.

{{< img src="developers/marketplace/marketplace_updated_overview.png" alt="The Datadog Marketplace page" style="width:100%" >}}

[101]: https://app.datadoghq.com/marketplace

{{% /tab %}}
{{< /tabs >}}

## Join the Datadog partner network

Before listing an integration on Datadog, first apply to the [Datadog Partner Network's][5] **Technology Partner** track. Once your application has been approved, you can begin developing your integration.

## Create a Datadog integration

### Agent-based integrations

Agent-based integrations use the [Datadog Agent][11] to submit data through checks written by Technology Partners. The implementation code for these integrations is hosted by Datadog. 

Agent integrations are best suited for collecting data from systems or applications that live in a local area network (LAN) or virtual private cloud (VPC). [Creating an Agent integration][2] requires you to publish and deploy your solution as a Python wheel (`.whl`).

### API-based integrations

API-based integrations can submit telemetry—such as metrics, traces, logs, and more—from external platforms using the [Datadog API][12]. Customers can then visualize and correlate this data alongside data from the rest of their stack, allowing them to quickly analyze and remediate issues. API-based integrations may also read data out of Datadog once customers [authorize access using OAuth][13]. 

Technology Partners write and host the implementation code that makes up the integration. [Creating an API integration][1] works well for Technology Partners building a connector between Datadog and another SaaS platform.

### Benefits

By creating an integration, you can achieve the following benefits:

Correlate your data with user observability data
: Leverage Datadog to increase the value of your platform by allowing customers to see the data from your platform alongside the rest of their technology stack.

Decrease mean-time-to-resolution (MTTR) for customers 
: When a customer's account is enriched with data from an integration, they are able to see a broader view of their entire stack, allowing them to debug and remediate issues more quickly. 

Increase adoption and visibility 
: Ensuring native functionality for Datadog reduces friction to adoption, and displaying a tile on the [Integrations page][10] or the [Marketplace page][17] provides key visibility to all of Datadog's customers.

### Responsibilities

As the author of the integration, you are responsible for maintaining the code and ensuring the integration functions properly across all [Datadog sites][15]. If you encounter any setup issues, [contact Support][16].

## Get started 

### Request a sandbox account

All Technology Partners can request a dedicated Datadog sandbox account to help develop their integration. This sandbox account has a free license that you can use to send in data, build out dashboards, and more. 

<div class="alert alert-info">If you are already a member of a Datadog organization (including a trial org), you may need to switch to your newly created sandbox. For more information, see the <a href="https://docs.datadoghq.com/account_management/org_switching/">Account Management documentation</a>.</div>

To request a sandbox account:

1. Login to the [Datadog Partner Portal][5].
2. On your personal homepage, click on the **Learn More** button under **Sandbox Access**.
3. Select **Request Sandbox Upgrade**.

Creating a developer sandbox may take up to one or two business days. Once your sandbox is created, you can [invite new members from your organization][6] to collaborate with.

### Explore learning resources

Once you've joined the **Technology Partner** track and requested a sandbox account, you can learn more about developing an offering by:

* Completing the on-demand [**Introduction to Datadog Integrations**][7] course on the [Datadog Learning Center][8].
* Reading the documentation about creating [API-based integrations][1] and setting up an [OAuth 2.0 client for API-based integrations][9].
* Reading the documentation about creating [Agent-based integrations][2].

For more information about selling a Datadog integration or other type of offering, see [Build a Marketplace Offering][4].

## Further reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://docs.datadoghq.com/developers/integrations/api_integration/
[2]: https://docs.datadoghq.com/developers/integrations/agent_integration/
[3]: https://docs.datadoghq.com/integrations/
[4]: https://docs.datadoghq.com/developers/integrations/marketplace_offering/
[5]: https://partners.datadoghq.com/
[6]: https://docs.datadoghq.com/account_management/users/#add-new-members-and-manage-invites
[7]: https://learn.datadoghq.com/courses/intro-to-integrations
[8]: https://learn.datadoghq.com/
[9]: https://docs.datadoghq.com/developers/authorization/
[10]: https://app.datadoghq.com/integrations
[11]: https://docs.datadoghq.com/agent/
[12]: https://docs.datadoghq.com/api/latest/
[13]: https://docs.datadoghq.com/developers/authorization/
[14]: https://docs.datadoghq.com/metrics/custom_metrics/
[15]: https://docs.datadoghq.com/getting_started/site/
[16]: https://docs.datadoghq.com/help/
[17]: https://app.datadoghq.com/marketplace