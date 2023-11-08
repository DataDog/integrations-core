# Kafka Consumer integration Dev Setup

## Install `librdkafka`

The kafka-consumer integration leverages the [confluent-kafka](https://github.com/confluentinc/confluent-kafka-python) library. To support Kerberos authentication, this library needs to be built from source, more info can be found [here](https://github.com/confluentinc/confluent-kafka-python#install). 

To be able to build the test environments and run the tests, you'll need to manually install `librdkafka` on your host. To do so on MacOS, simply run:

```commandline
brew install librdkafka
```

For other systems, you can follow the instructions [here](https://github.com/confluentinc/confluent-kafka-python/blob/master/INSTALL.md#install-from-source). 

Once done, you can run `ddev test kafka_consumer`, the `confluent-kafka` will be built from source.

Note: On CI, the dependencies are built in the `32_install_kerberos.sh` script.

## Troubleshooting

### fatal error: 'librdkafka/rdkafka.h' file not found

If you face this issue:

```commandline
      /private/var/folders/hq/d80ndr2x68g21s07h1nww6qw0000gp/T/pip-install-1v8fm2o0/confluent-kafka_f0f65a0360e648168d1dbcd50ec93912/src/confluent_kafka/src/confluent_kafka.h:23:10: fatal error: 'librdkafka/rdkafka.h' file not found
      #include <librdkafka/rdkafka.h>
               ^~~~~~~~~~~~~~~~~~~~~~
```

1. Make sure you installed `librdkafka` (see the previous section).
2. You might need to set the `C_INCLUDE_PATH` and `LIBRARY_PATH` environments variable to load `librdkafka` when building `confluent-kafka`. For instance: `C_INCLUDE_PATH=/opt/homebrew/Cellar/librdkafka/2.1.1/include/ LIBRARY_PATH=/opt/homebrew/Cellar/librdkafka/2.1.1/lib ddev test kafka_consumer`. (be sure to use the same version as declared in the `pyproject.toml` file). Setting these environment variables is only needed when the test environment is built (or rebuilt with the `--recreate` option).  

### Barebones connection

If you are unable to connect to your Kafka cluster in your Agent, you can use the script in `tests/python_client/script.py` to run a barebones connection directly to the cluster for debugging. This script will attempt a connection and then fetch all of the consumer groups for that configuration.