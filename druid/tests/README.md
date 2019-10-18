# Druid Dev Readme

## Quick Start Druid for testing statsd emitter

1) Download Druid and extract files: https://druid.apache.org/downloads.html

2) Extract Druid

3) Follow main [README.md](../README.md) "Connect Druid to DogStatsD" step for setting up Druid.  

   The java properties that need to be updated is located here: `<DRUID>/conf/druid/single-server/micro-quickstart/_common/common.runtime.properties`  

4) Start the Datadog Agent

5) Start Druid `./bin/start-micro-quickstart`. 

   Druid will start sending metrics to the agent.
   