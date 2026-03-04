# CHANGELOG - Kafka Actions

<!-- towncrier release notes start -->

## 2.3.0 / 2026-02-19

***Added***:

* Add `enable_legacy_tags_normalization` option to preserve hyphens in tag values when set to false. ([#22303](https://github.com/DataDog/integrations-core/pull/22303))
* Bump confluent-kafka to 2.13.0 ([#22630](https://github.com/DataDog/integrations-core/pull/22630))

## 2.2.0 / 2026-02-04 / Agent 7.76.0

***Security***:

* Bump protobuf version to 6.33.5 ([#22522](https://github.com/DataDog/integrations-core/pull/22522))

## 2.1.0 / 2026-02-04 / Agent 7.75.3

***Security***:

* Bump protobuf version to 6.33.5 ([#22522](https://github.com/DataDog/integrations-core/pull/22522))

## 2.0.1 / 2026-01-06 / Agent 7.75.0

***Fixed***:

* Fix Kafka message decoding when using Protobuf with schema registry. ([#22265](https://github.com/DataDog/integrations-core/pull/22265))

## 2.0.0 / 2025-12-22

***Changed***:

* Send Kafka messages to backend as data streams events instead of regular Datadog events ([#22208](https://github.com/DataDog/integrations-core/pull/22208))

## 1.0.0 / 2025-12-22

***Added***:

* Initial Release ([#21951](https://github.com/DataDog/integrations-core/pull/21951))
