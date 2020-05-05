---
title: Introduction to Agent-based integrations
kind: documentation
aliases:
  - /guides/agent_checks/
  - /agent/agent_checks
  - /developers/agent_checks/
---

## Why create an integration?

[Custom Checks][1] are great for occasional reporting, or in cases where the data source is either unique or very limited. For more general use-cases - such as application frameworks, open source projects, or commonly-used software - it makes sense to write an integration.

Metrics reported from accepted integrations are not counted as custom metrics, and therefore don't impact your custom metric allocation. (Integrations that emit potentially unlimited metrics may still be considered custom.) Ensuring native support for Datadog reduces friction to adoption, and incentivizes people to use your product, service, or project. Also, being featured within the Datadog ecosystem is a great avenue for added visibility.

### What's the process?

The initial goal is to generate some code that collects the desired metrics in a reliable way, and to ensure that the general integration framework is in place. Start by writing the basic functionality as a custom Check, then fill in the framework details from the [Create an integration documentation][2].

Next, open a pull request against the [integrations-extras repository][3]. This signals to Datadog that you're ready to start reviewing code together. Don't worry if you have questions about tests, Datadog internals, or other topics - the integrations team is ready to help, and the pull request is a good place to go over those concerns. Be sure to take advantage of the [Community Office Hours][4] as well!

Once the integration has been validated (functionality, framework compliance, and general code quality) it will be merged into Extras. Once there, it becomes part of the Datadog ecosystem. Congratulations!

### What are your responsibilities?

Going forward, you - as the author of the code - are now the active maintainer of the integration. You're responsible for maintaining the code and ensuring the integration's functionality. There is no specific time commitment, but we do ask that you only agree to become a maintainer if you feel that you can take care of the code for the foreseeable future. Datadog extends support on a best-effort basis for Extras, so you won't be on your own!

## Let's get started!

All of the details-including prerequisites, code examples, and more-are in the [Create a new integration][2] documentation.

[1]: https://docs.datadoghq.com/developers/write_agent_check/
[2]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/new_check_howto.md
[3]: https://github.com/DataDog/integrations-extras
[4]: https://docs.datadoghq.com/developers/office_hours/
