# TLS/SSL

-----

TLS/SSL is widely used to provide communications over a secure network. Many of the software that Datadog supports has features to allow TLS/SSL,
and thus the Datadog Agent may need to connect via TLS/SSL in order to get metrics.


## Getting Started
Starting with Agent 7.24, checks that are TLS/SSL compatible should no longer manually create a raw `ssl.SSLContext`.
Instead, check implementations should use `AgentCheck.get_tls_context()` to obtain a TLS/SSL context. 

`get_tls_context()` allows a few optional parameters which may be helpful when developing integrations.

::: datadog_checks.base.AgentCheck.get_tls_context