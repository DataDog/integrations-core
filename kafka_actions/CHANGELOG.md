# CHANGELOG - Kafka Actions

<!-- towncrier release notes start -->

## 2.4.1 / 2026-03-24

***Fixed***:

* Return early from consume_messages when end of partition is reached instead of waiting for timeout ([#23004](https://github.com/DataDog/integrations-core/pull/23004))

## 2.4.0 / 2026-03-18

***Added***:

* Update dependencies ([#22707](https://github.com/DataDog/integrations-core/pull/22707))
* Add support for Kerberos (GSSAPI), OAuth (OAUTHBEARER with OIDC and AWS MSK IAM), and TLS/SSL certificate authentication, matching kafka_consumer authentication options. ([#22818](https://github.com/DataDog/integrations-core/pull/22818))
* Bump `confluent-kafka` to 2.13.2 ([#22829](https://github.com/DataDog/integrations-core/pull/22829))
* Add Schema Registry support for automatic schema fetching when reading Kafka messages with protobuf, avro, or JSON schemas. ([#22867](https://github.com/DataDog/integrations-core/pull/22867))
* Add start_timestamp support for read_messages action to seek by timestamp instead of offset. ([#22893](https://github.com/DataDog/integrations-core/pull/22893))

***Fixed***:

* Fix consumer timeout when reading latest N messages by seeking back from high watermark instead of positioning at OFFSET_END ([#22797](https://github.com/DataDog/integrations-core/pull/22797))
* Use the actual Kafka message timestamp instead of current time for message_timestamp in read_messages events. ([#22895](https://github.com/DataDog/integrations-core/pull/22895))

## 2.3.0 / 2026-02-19

***Added***:

* Add `enable_legacy_tags_normalization` option to preserve hyphens in tag values when set to false. ([#22303](https://github.com/DataDog/integrations-core/pull/22303))
* Bump confluent-kafka to 2.13.0 ([#22630](https://github.com/DataDog/integrations-core/pull/22630))

## 2.2.0 / 2026-02-04

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
