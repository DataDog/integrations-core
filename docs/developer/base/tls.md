# TLS/SSL

-----

TLS/SSL is widely used to provide communications over a secure network. Many of the software that Datadog supports has features to allow TLS/SSL.
Therefore, the Datadog Agent may need to connect with TLS/SSL to get metrics.


## Getting started
For Agent v7.24+, checks compatible with TLS/SSL should not manually create a raw `ssl.SSLContext`.
Instead, check implementations should use `AgentCheck.get_tls_context()` to obtain a TLS/SSL context.

`get_tls_context()` allows a few optional parameters which may be helpful when developing integrations.

::: datadog_checks.base.checks.base.AgentCheck.get_tls_context

## Distrusted CA keys
TLS connections whose verified certificate chain contains a distrusted CA public key fail with an `ssl.SSLCertVerificationError`.
Keys are matched by the SHA-256 of their DER `SubjectPublicKeyInfo`. The built-in list holds the compromised eMudhra emSign G3 keys, and the Agent setting `tls_distrusted_spki_sha256` can add more but cannot remove one.

The check covers every connection made with Python's `ssl` module or pyOpenSSL in the Agent's Python process, including contexts that checks or libraries build themselves, so checks don't need to do anything to get it.
