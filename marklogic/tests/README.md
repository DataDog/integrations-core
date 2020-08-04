# Test environment for MarkLogic

This integration can be tested using the Docker Compose environment.

In order to have the MarkLogic docker image, you need to `docker login` and get the docker image here https://hub.docker.com/_/marklogic.

## Cluster mode

The cluster environment is not working on CI yet (TODO).
To start a cluster environment for testing, uncomment the cluster part in the `dd_environment` fixture in `conftest.py`, and comment the standalone part. Then use `ddev env start marklogic <ENV>` as usual.
