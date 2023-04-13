---
title: Build A Marketplace Offering
type: documentation
aliases: 
- 'developers/marketplace/'
dependencies: "https://github.com/DataDog/integrations-core/blob/alai97/add-marketplace-documentation/docs/dev/marketplace_offering.md"
further_reading:
- link: "https://www.datadoghq.com/partner/"
  tag: "Partner Network"
  text: "Datadog Partner Network"
- link: "https://www.datadoghq.com/blog/datadog-marketplace/"
  tag: "Blog"
  text: "Expand your monitoring reach with the Datadog Marketplace"
- link: "/developers/integrations/marketplace_offering/"
  tag: "Documentation"
  text: "Learn how to develop a Marketplace offering"
- link: "/developers/datadog_apps/"
  tag: "Documentation"
  text: "Learn about Datadog Apps"
---

## Overview
Add why join the Marketplace (GTM,)

The Datadog Marketplace is a digital marketplace where Datadog Technology Partners can list their paid offerings to Datadog users. Datadog customers can access paid integration tiles on the [**Marketplace** page][2].

{{< img src="developers/marketplace/marketplace_overview.png" alt="The Datadog Marketplace page" style="width:100%" >}}

While the **Integrations** page includes integrations and Datadog Apps built by Datadog and Technology Partners at no cost, the **Marketplace** page is a commercial platform for Datadog customers and Technology Partners to buy and sell a variety of offerings including Agent-based or API-based integrations, Datadog Apps, software, and professional services.

## Join the Datadog partner network

Before requesting access to the Datadog Marketplace, first apply to join the [Datadog Partner Network's][3] **Technology Partners** track. As a Datadog Technology Partner, you can either develop an [Agent-based or API integration][4] or a [Datadog App][5], or list your SaaS license or professional services offering.

## Apply for a sandbox account

All Technology Partners can request a dedicated sandbox Datadog account to aid in their development.

To request a sandbox account:

1. Log into the [Datadog Partner Portal][6].
2. On your personal homepage, click on the **Learn More** button under **Sandbox Access**.
3. Select **Request Sandbox Upgrade**.

<div class="alert alert-info">If you are already a member of a Datadog organization (including a trial org), you may need to switch to your newly created sandbox. For more information, see the <a href="https://docs.datadoghq.com/account_management/org_switching/">Account Management documentation</a>.</div>

Creating a developer sandbox may take up to one or two business days. Once your sandbox is created, you can [invite new members from your organization][7] to collaborate with.

## Explore learning resources

Once you've joined the Technology Partners track and requested a sandbox account, you can start learning about developing Datadog integrations and additional offerings by:

* Completing the on-demand [**Introduction to Datadog Integrations**][8] course on the [Datadog Learning Center][9].
* Joining the Marketplace Engineering Office Hours through the public [Datadog Slack channel][10].
* Reading the documentation about [Datadog Apps][5] if you want to build a custom widget that integrates external data and actions with Datadog dashboards.
* Reading the documentation about setting up an [OAuth 2.0 client][11] for Agent-based or API-based integrations and Datadog Apps.

## List an offering on Marketplace

All Technology Partners can list a free integration on the **Integrations** page or a commercial offering on the **Marketplace** page. Additional offerings on Datadog Marketplace may include:

Integrations
: Marketplace integrations that submit or pull third-party data through the [Datadog Agent][15] or an [API][16]. These integrations contain out-of-the-box metrics, events, or service checks.

Software licenses
: SaaS licenses enable you to deliver and license software solutions to customers through the Datadog Marketplace.

UI extensions or applications
: An application (such as a [Datadog App][5]) with a [tile-only listing][17] on the Datadog Marketplace.

Professional services
: [Professional services][18] enable you to offer your team's services for implementation, support, or management for a set period of time.

### Request access to Marketplace

To request access to the private Marketplace repository, email <a href="mailto:marketplace@datadoghq.com">marketplace@datadoghq.com</a>. A Marketplace offering requires files and information such as pricing plans. Once you have been granted access, you can review an [example pull request][12] in the Marketplace repository with annotations and best practices.

To get started with creating an offering, see [Create a Tile][13].

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://app.datadoghq.com/integrations
[2]: https://app.datadoghq.com/marketplace
[3]: https://partners.datadoghq.com/
[4]: https://docs.datadoghq.com/developers/integrations/new_check_howto/
[5]: https://docs.datadoghq.com/developers/datadog_apps
[6]: https://partners.datadoghq.com/English/
[7]: /account_management/users/#add-new-members-and-manage-invites
[8]: https://learn.datadoghq.com/courses/intro-to-integrations
[9]: https://learn.datadoghq.com/
[10]: https://chat.datadoghq.com/
[11]: https://docs.datadoghq.com/developers/authorization/
[12]: https://github.com/DataDog/marketplace/pull/107
[13]: https://docs.datadoghq.com/developers/integrations/create_a_tile
[14]: https://docs.datadoghq.com/developers/integrations/api_integration/
[15]: https://docs.datadoghq.com/integrations/create_a_tile/#agent-based-integrations
[16]: https://docs.datadoghq.com/integrations/create_a_tile/#rest-api-integrations
[17]: https://docs.datadoghq.com/integrations/create_a_tile/#datadog-apps
[18]: https://docs.datadoghq.com/integrations/create_a_tile/#saas-license-or-professional-service-offerings
