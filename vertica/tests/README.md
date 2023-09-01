# Test environment for Vertica

This integration can be tested using the Docker Compose environment.

We use a custom Dockerfile that uses the [official vertica-ce images](https://hub.docker.com/r/vertica/vertica-ce)
as a base, but customizes the entrypoint to avoid loading data and extensions in order to shorten startup times.
