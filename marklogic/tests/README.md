# Test environment for MarkLogic

This integration can be tested using the Docker Compose environment.

In order to have the MarkLogic docker image, you need to `docker login` and get the docker image here https://hub.docker.com/_/marklogic.

## Cluster mode

The cluster environment is not working on CI yet (TODO).
To start a cluster environment for testing, change the `dd_environment` fixture in the `conftest.py` by the cluster docker-compose: 
```python
@pytest.fixture(scope="session")
def dd_environment():
    # type: () -> Generator[Dict[str, Any], None, None]

    # Cluster
    compose_file = os.path.join(HERE, 'compose', 'cluster/docker-compose.yml')
    with docker_run(
        compose_file=compose_file,
        conditions=[
            CheckDockerLogs(compose_file, r'Detected quorum'),
            WaitFor(setup_admin_user),
            WaitFor(setup_datadog_user),
        ],
    ):
        yield CHECK_CONFIG
```
Then use `ddev env start marklogic <ENV>` as usual.
