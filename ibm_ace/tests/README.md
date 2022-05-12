# IBM ACE Integration E2E

Metric collection is disabled by default in the E2E environment. To enable metric collection for development and testing, update the `dd_environment` fixture in `/tests/conftest.py` to use the `instance` fixture instead of `instance_no_subscriptions`.


# IBM ACE Integration Dev Setup for MacOS

The IBM ACE integration requires the same setup as the IBM MQ integration. See the [instructions](https://github.com/DataDog/integrations-core/blob/master/ibm_mq/tests/README.md).
