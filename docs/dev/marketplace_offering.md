---
title: Build A Marketplace Offering
type: documentation
aliases: 
- 'developers/marketplace/'
further_reading:
- link: "https://www.datadoghq.com/partner/"
  tag: "Partner Network"
  text: "Datadog Partner Network"
- link: "https://www.datadoghq.com/blog/datadog-marketplace/"
  tag: "Blog"
  text: "Expand your monitoring reach with the Datadog Marketplace"
- link: "/developers/integrations/create_a_tile"
  tag: "Documentation"
  text: "Create a Tile"
- link: "/developers/integrations/agent_integration"
  tag: "Documentation"
  text: "Create an Agent-based Integration"
---

## Overview

The [Datadog Marketplace][2] is a digital marketplace where Technology Partners can list their paid offerings to Datadog users.  

While the **Integrations** page includes integrations built by both Datadog and Technology Partners at no cost, the **Marketplace** page is a commercial platform for Datadog customers and Technology Partners to buy and sell a variety of offerings, including Agent-based or API-based integrations, software licenses, and professional services.

{{< img src="developers/marketplace/marketplace_overview.png" alt="The Datadog Marketplace page" style="width:100%" >}}

## List an offering 

The following types of offerings are supported on the Datadog Marketplace:

Integrations
: Marketplace integrations that submit third-party data to (or pull data from) a user's Datadog account through the [Datadog Agent][19] or the [Datadog API][15]. These integrations can contain a variety of data types, such as metrics, events, logs, traces, and more.

Software licenses
: Software licenses enable you to deliver and license software solutions to customers through the Datadog Marketplace.

Professional services
: Professional services enable you to offer your team's services for implementation, support, or management for a set period of time.

## Join the Datadog Marketplace 

Marketplace Partners have unique benefits that are not available to Technology Partners who list out-of-the-box integrations:
 
- **Go-to-market collaboration** including a blog post, a quote for a press release, and social media amplification, with access to dedicated sales and marketing resources focused on accelerating partner growth. 
- **Training and support** for internal sales enablement.
- **Exclusive opportunities to sponsor** conferences and events (such as [Datadog DASH][20]) at a discounted rate.
- **Generate new leads** from user discovery.

## Join the Datadog partner network

Before listing an offering on the Datadog Marketplace, you first need to apply to the [Datadog Partner Network's][3] **Technology Partner** track. Once your application has been approved, you can begin developing your offering.

## Request a sandbox account

All Technology Partners can request a dedicated Datadog sandbox account to aid in their development.

To request a sandbox account:

1. Login to the [Datadog Partner Portal][6].
2. On your personal homepage, click on the **Learn More** button under **Sandbox Access**.
3. Select **Request Sandbox Upgrade**.

<div class="alert alert-info">If you are already a member of a Datadog organization (including a trial org), you may need to switch to your newly created sandbox. For more information, see the <a href="https://docs.datadoghq.com/account_management/org_switching/">Account Management documentation</a>.</div>

Creating a developer sandbox may take up to one or two business days. Once your sandbox is created, you can [invite new members from your organization][7] to collaborate with.

## Request access to Marketplace

To request access to the private Marketplace repository, email <a href="mailto:marketplace@datadoghq.com">marketplace@datadoghq.com</a>. Once you have been granted access, you can review an [example pull request][12] in the Marketplace repository with annotations and best practices.

## Coordinate go-to-market (GTM) opportunities

Once a Marketplace tile is live, Technology Partners can meet with Datadog's Partner Marketing team to coordinate a joint go-to-market (GTM) strategy, which includes the following:

- A Datadog quote for partner press releases
- A blog post on the [Datadog Monitor][21]
- Amplification of social media posts

## Get started

To get started with creating an API-based integration, software license, or professional service, see [Create a Tile][13]. If you're interesting in building an Agent-based integration and selling it on the Datadog Marketplace, see [Create an Agent-based Integration][19].

## Further reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://app.datadoghq.com/integrations
[2]: https://app.datadoghq.com/marketplace
[3]: https://partners.datadoghq.com/
[5]: https://docs.datadoghq.com/developers/datadog_apps
[6]: https://partners.datadoghq.com/English/
[7]: /account_management/users/#add-new-members-and-manage-invites
[8]: https://learn.datadoghq.com/courses/intro-to-integrations
[9]: https://learn.datadoghq.com/
[10]: https://chat.datadoghq.com/
[11]: https://docs.datadoghq.com/developers/authorization/
[12]: https://github.com/DataDog/marketplace/pull/107
[13]: https://docs.datadoghq.com/developers/integrations/create_a_tile
[15]: https://docs.datadoghq.com/developers/integrations/api_integration
[19]: https://docs.datadoghq.com/developers/integrations/agent_integration
[20]: https://www.dashcon.io/
[21]: https://www.datadoghq.com/blog/
