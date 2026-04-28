# Memcached Integration - Development

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

Run all unit and integration tests:

```shell
ddev --no-interactive test mcache
```

Run a specific test:

```shell
ddev --no-interactive test mcache -- -k <PYTEST_FILTER_STRING>
```

Auto-format and lint:

```shell
ddev test -fs mcache
```

## E2E Tests

E2E tests spin up Docker containers running Memcached and a Datadog Agent.

1. List available environments:

   ```shell
   ddev env show mcache
   ```

2. Start an environment, run its E2E tests, then stop it:

   ```shell
   ddev env start --dev mcache py3.13
   ddev env test --dev mcache py3.13
   ddev env stop mcache py3.13
   ```

3. To recreate the environment from scratch (e.g. after dependency changes):

   ```shell
   ddev env test --dev --recreate mcache py3.13
   ```

### Agent Autodiscovery E2E

The `py3.13-ad-1.6` environment exercises the Agent's container autodiscovery using
the integration's `auto_conf.yaml`. It starts a single default-port Memcached container
on the Docker bridge network, mounts the host Docker socket into the Agent container,
and verifies the Agent discovers the container via the Docker listener.

```shell
ddev env start --dev mcache py3.13-ad-1.6
ddev env test  --dev mcache py3.13-ad-1.6
ddev env stop  mcache py3.13-ad-1.6
```

Only the default-port bridge-network case is covered today. Other cases (port-forwarded,
non-default in-container port, `--network=host`, SASL-authenticated autodiscovery,
process autodiscovery) are tracked in the DSCVR "Integrations autodiscovery exploration"
Confluence page and will be added as the associated upstream issues are fixed.

The Agent reads `auto_conf.yaml` via a file-level Docker bind-mount of the source-tree
copy at `mcache/datadog_checks/mcache/data/auto_conf.yaml`. Editing the file between
test runs requires restarting the environment (`ddev env stop` then `ddev env start`)
because tools like `git checkout` replace the file's inode and break the live mount.
