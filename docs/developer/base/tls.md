# TLS/SSL

-----

TLS/SSL is widely used to provide communications over a secure network. Many of the software that Datadog supports has features to allow TLS/SSL,
and thus the Datadog Agent may need to connect via TLS/SSL in order to get metrics.


## Getting Started
If the Agent is connecting to an integration with TLS/SSL, it will need to set configuration parameters in the `conf.yaml` file for the Agent to use.

### Configuration options:

#### `tls_verify`
    example: true
    type: boolean
    
    Instructs the check to validate the TLS certificate(s) of the service(s).

#### `tls_ca_cert`
    example: <CA_CERT_PATH>
    type: string
    
    The path to a file of concatenated CA certificates in PEM format or a directory
    containing several CA certificates in PEM format. If a directory, the directory
    must have been processed using the c_rehash utility supplied with OpenSSL. See:
    https://www.openssl.org/docs/manmaster/man3/SSL_CTX_load_verify_locations.html
    Setting this implicitly sets `tls_verify` to true.

#### `tls_cert`
    example: <CERT_PATH>
    type: string

    The path to a single file in PEM format containing a certificate as well as any
    number of CA certificates needed to establish the certificate's authenticity for
    use when connecting to services. It may also contain an unencrypted private key to use.
    Setting this implicitly sets `tls_verify` to true.

#### `tls_private_key`
    example: <PRIVATE_KEY_PATH>
    type: string

    The unencrypted private key to use for `tls_cert` when connecting to services. This is
    required if `tls_cert` is set and it does not already contain a private key.
    Setting this implicitly sets `tls_verify` to true.
    
#### `tls_private_key_password`
    example: <PRIVATE_KEY_PASSWORD>
    type: string

    Optional password to decrypt tls_private_key.
    Setting this implicitly sets `tls_verify` to true.
    
#### `tls_validate_hostname`
    example: true
    type: boolean

    Verifies that the server's cert hostname matches the one requested.



## TLS/SSL Context
Starting with Agent 7.24, checks that are TLS/SSL compatible should no longer manually create a raw `ssl.SSLContext`.
Instead, check implementations should use [`get_tls_context()`](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/base.py#L325)
to obtain a TLS/SSL context. 
`get_tls_context()` allows a few optional parameters which may be helpful when developing integrations.

### Optional parameters
#### `refresh`
    type: bool

    Refresh the context by creating and replacing the current one.


#### `overrides`
    type: Dict[AnyStr, Any]

    A dictionary containing TLS config parameters that will override the parameters in `conf.yaml`.
