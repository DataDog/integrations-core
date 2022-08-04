---
title: Introduction to Agent-based Integrations
kind: documentation
aliases:
  - /guides/agent_checks/
  - /agent/agent_checks
  - /developers/agent_checks/
---

If you need to send data to Datadog that isn't supported by the Agent or an existing agent integration, you can either create a Custom Check, or create a Datadog integration. To find out if creating an integration is the right solution for your use case, see [Creating your own solution][89]. Read on if you're ready to find out more about creating an integration.

## Datadog integration categories

Datadog integrations fall into three categories:
- [Core integrations](https://github.com/datadog/integrations-core) are developed and maintained by Datadog. These integrations come packaged with the Datadog Agent.
- [Extras integrations]([integrations-extras](https://github.com/datadog/integrations-extras)) are developed and maintained by the community. If you're looking to create and publish your own integration, this is where you'll open your pull request.
- Marketplace integrations are developed and maintained by marketplace partners. The marketplace integrations repo is private, which is why you don't see a link to it here. The development process is similar to the one for Extras integrations, but to release on the marketplace, you need to become a marketplace partner.

## What's the process?

The initial goal is to generate some code that collects the desired metrics in a reliable way, and to ensure that the general integration framework is in place. Start by writing the basic functionality of your integration as a [Custom Check][1], then work your way through [Getting Started with integrations][2] to fill out the integration framework.

Next, open a pull request against the [integrations-extras repository][3]. This signals to Datadog that you're ready to start reviewing code together. Don't worry if you have questions about tests, Datadog internals, or other topics - the integrations team is ready to help, and the pull request is a good place to go over those concerns. Be sure to take advantage of the [Community Office Hours][4] as well!

Once the integration has been validated (functionality, framework compliance, and general code quality) it is merged into Extras. Once there, it becomes part of the Datadog ecosystem. Congratulations!

### What are your responsibilities?

Going forward, you, as the author of the code, are the active maintainer of the integration. You're responsible for maintaining the code and ensuring the integration's functionality. There is no specific time commitment, but you must be a maintainer and take care of the code for the foreseeable future. Datadog extends support on a best-effort basis for Extras, so you are not alone.

## Let's get started!

To get started, head over to 

## Further Reading

Additional helpful documentation, links, and articles:

- [Datadog Learning Center: Introduction to Integrations][6]

[89]: https://docs.datadoghq.com/developers/#creating-your-own-solution
[1]: https://docs.datadoghq.com/developers/write_agent_check/
[2]: https://docs.datadoghq.com/developers/integrations/new_check_howto/
[3]: https://github.com/DataDog/integrations-extras
[4]: https://docs.datadoghq.com/developers/office_hours/
[5]: https://docs.datadoghq.com/developers/#custom-check-versus-integration
[6]: https://learn.datadoghq.com/enrol/index.php?id=38
[90]: https://learn.datadoghq.com/course/view.php?id=38
