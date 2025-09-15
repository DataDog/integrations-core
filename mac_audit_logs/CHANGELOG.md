# CHANGELOG - mac_audit_logs

<!-- towncrier release notes start -->

## 1.0.1 / 2025-09-05

***Fixed***:

* Run `auditreduce` subprocess with `TZ=UTC` in the environment to ensure the timestamps queried match within the window of the audit file. ([#21208](https://github.com/DataDog/integrations-core/pull/21208))

## 1.0.0 / 2025-07-10 / Agent 7.69.0

***Added***:

* Initial Release ([#19989](https://github.com/DataDog/integrations-core/pull/19989))
