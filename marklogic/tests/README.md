# Test environment for MarkLogic

Test this integration using the Docker Compose environment.

To get the MarkLogic Docker image, run `docker login` and download the Docker image here https://hub.docker.com/r/marklogicdb/marklogic-db.

## E2E testing on Apple Silicon
[Starting with MarkLogic 11 and above](https://docs.marklogic.com/11.0/guide/release-notes/en/new-features-in-marklogic-11/install-on-macos-running-on-apple-m1-processors.html), you can run MarkLogic on ARM with Rosetta 2 emulation.

Docker Desktop 4.16+ supports Rosetta emulation for x86/amd64 on Apple Silicon, although you will need to enable this experimental feature in the settings. 
1. Under `Settings` -> `General` tab, click on `Use Virtualization framework` to enable [Virtualization](https://developer.apple.com/documentation/virtualization). 
1. Then go to the `Features in development` tab, and click on `Use Rosetta for x86/amd64 emulation on Apple Silicon` under `Beta features`. 
1. Apply and restart Docker Desktop for changes to go into effect.

Note: MarkLogic 9 and 10 still do not support ARM.

## Cluster mode

The cluster environment is not working on CI yet (TODO).
To start a cluster environment for testing, change the `dd_environment` fixture in the `conftest.py` by the cluster `docker compose`: 
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
            WaitFor(setup_datadog_users),
        ],
    ):
        yield CHECK_CONFIG
```
Then use `ddev env start marklogic <ENV>` as usual.
