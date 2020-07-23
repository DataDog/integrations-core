# Druid Dev Readme

## Quick start Druid for testing StatsD emitter

1) Download Druid and the extract files: https://druid.apache.org/downloads.html

2) Extract Druid.

3) Follow the main [README.md](../README.md) "Connect Druid to DogStatsD" step for setting up Druid.  

Update the Java properties located at: `<DRUID>/conf/druid/single-server/micro-quickstart/_common/common.runtime.properties`  

4) Start the Datadog Agent.

5) Start Druid `<DRUID>/bin/start-micro-quickstart`. 

   Druid will start sending metrics to the Agent.
   
