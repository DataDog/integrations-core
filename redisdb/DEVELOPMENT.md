# Redis Integration - Development

## Prerequisites

Install `ddev` and configure it to point at this repo:

```shell
pip install ddev
ddev config set repos.core /path/to/integrations-core
```

The test matrix requires Python 3.13. Install it via pyenv if needed:

```shell
curl https://pyenv.run | bash
# Add pyenv to your shell (follow the printed instructions), then:
pyenv install 3.13
pyenv global 3.13
```

## Unit and Integration Tests

Run all unit and integration tests across all matrix environments (Redis 5.0, 6.0, 7.0, 8.0, cloud):

```shell
ddev --no-interactive test redisdb
```

Run a specific test:

```shell
ddev --no-interactive test redisdb -- -k <PYTEST_FILTER_STRING>
```

Auto-format and lint:

```shell
ddev test -fs redisdb
```

## E2E Tests

E2E tests spin up Docker containers running Redis and a Datadog Agent.

1. List available environments:

   ```shell
   ddev env show redisdb
   ```

2. Start an environment, run its E2E tests, then stop it:

   ```shell
   ddev env start --dev redisdb py3.13-7.0
   ddev env test --dev redisdb py3.13-7.0
   ddev env stop redisdb py3.13-7.0
   ```

   Replace `py3.13-7.0` with any environment from `ddev env show` (e.g. `py3.13-5.0`, `py3.13-6.0`, `py3.13-8.0`).

3. To recreate the environment from scratch (e.g. after dependency changes):

   ```shell
   ddev env test --dev --recreate redisdb py3.13-7.0
   ```

### Notes

- The `cloud` environment (`py3.13-cloud`) requires external cloud credentials and cannot be run locally.
- E2E tests are marked with `@pytest.mark.e2e` and are excluded from unit/integration test runs automatically.

### Agent Autodiscovery E2E

The `py3.13-ad-7.0` environment exercises the Agent's container autodiscovery using
the integration's `auto_conf.yaml`. It starts a single default-port Redis container on the
Docker bridge network, mounts the host Docker socket into the Agent container, and verifies
the Agent discovers the container via the Docker listener.

```shell
ddev env start --dev redisdb py3.13-ad-7.0
ddev env test  --dev redisdb py3.13-ad-7.0
ddev env stop  redisdb py3.13-ad-7.0
```

Only the default-port bridge-network case is covered today. Other cases (port-forwarded,
non-default in-container port, `--network=host`, process autodiscovery) are tracked in the
DSCVR "Integrations autodiscovery exploration" Confluence page and will be added as the
associated upstream issues are fixed.
