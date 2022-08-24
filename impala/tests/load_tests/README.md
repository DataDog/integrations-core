# Impala load test environment

This folder contains a set of file to set up an Impala environment with: 

- 1 statestore
- 1 catalog
- 3 daemons 
- 1 hive metastore
- A docker container that will request one of the daemon to generate traffic

This environment was used to generate more metrics to tests the dashboards. I had to write it myself because the docker-compose file and scripts from the official Impala repository requires to run some commands manually. 

To deploy it:

1. Run `docker compose up`. It will downloads the images if needed and build the custom data-loader.
2. (optional) You can use the `conf.yaml` file to configure your agent. Be sure the paths to the logs are correctly configured (they should be in `./logs`).

The Impala services will expose their web-ui on:

- localhost:25000 for the daemon-1
- localhost:25100 for the daemon-2
- localhost:25100 for the daemon-3
- localhost:25010 for the statestore
- localhost:25020 for the catalog