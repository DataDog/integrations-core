# CHANGELOG - mac_audit_logs

<!-- towncrier release notes start -->

## 1.2.0 / 2025-11-26

***Added***:

* Bump minimum version of datadog-checks-base to 37.24.0 ([#21945](https://github.com/DataDog/integrations-core/pull/21945))

## 1.1.0 / 2025-10-02 / Agent 7.72.0

***Added***:

* Bump Python to 3.13 ([#21161](https://github.com/DataDog/integrations-core/pull/21161))
* Bump datadog-checks-base to 37.21.0 ([#21477](https://github.com/DataDog/integrations-core/pull/21477))

## 1.0.1 / 2025-09-05 / Agent 7.71.0

***Fixed***:

* Run `auditreduce` subprocess with `TZ=UTC` in the environment to ensure the timestamps queried match within the window of the audit file. ([#21208](https://github.com/DataDog/integrations-core/pull/21208))

## 1.0.0 / 2025-07-10 / Agent 7.69.0

***Added***:

* Initial Release ([#19989](https://github.com/DataDog/integrations-core/pull/19989))
