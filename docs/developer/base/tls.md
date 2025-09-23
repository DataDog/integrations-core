# TLS/SSL

-----

TLS/SSL is widely used to provide communications over a secure network. Many of the software that Datadog supports has features to allow TLS/SSL.
Therefore, the Datadog Agent may need to connect with TLS/SSL to get metrics.


## Getting started
For Agent v7.24+, checks compatible with TLS/SSL should not manually create a raw `ssl.SSLContext`.
Instead, check implementations should use `AgentCheck.get_tls_context()` to obtain a TLS/SSL context.

`get_tls_context()` allows a few optional parameters which may be helpful when developing integrations.

::: datadog_checks.base.checks.base.AgentCheck.get_tls_context
