# CHANGELOG - BentoML

<!-- towncrier release notes start -->

## 1.2.0 / 2025-10-31

***Added***:

* Add log config section ([#21580](https://github.com/DataDog/integrations-core/pull/21580))

***Fixed***:

* Add allowed values list on kerberos_auth field ([#20879](https://github.com/DataDog/integrations-core/pull/20879))
* Remap `endpoint` label to `bentoml_endpoint` to prevent it from clashing with OMv2 default `endpoint` tag ([#21777](https://github.com/DataDog/integrations-core/pull/21777))

## 1.1.0 / 2025-10-02 / Agent 7.72.0

***Added***:

* Bump datadog-checks-base to 37.21.0 ([#21477](https://github.com/DataDog/integrations-core/pull/21477))

## 1.0.0 / 2025-09-05 / Agent 7.71.0

***Added***:

* Add BentoML integration ([#21232](https://github.com/DataDog/integrations-core/pull/21232))
