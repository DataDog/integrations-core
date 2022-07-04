# Test environment for Vertica

This integration can be tested using the Docker Compose environment.

Because there is no official image for version 9, we are relying on a [community maintained image](https://hub.docker.com/r/jbfavre/vertica.).

For versions 10+, we have our own Dockerfile that uses the [official vertica-ce images](https://hub.docker.com/r/vertica/vertica-ce)
as a base, but customizes the entrypoint to avoid loading data to shorten startup times.
