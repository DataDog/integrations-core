# Tests

## Testing Guidelines

This check has 2 test matrix, one detailing the test type:

* unit tests (no need for a Redis instance running)
* integration tests (a Redis instance must run locally)

another matrix defines the Redis versions to be used with integration tests:

* redis 3.2
* redis 4.0

The first matrix is handled by pytest using `mark`: tests that need a running redis instance must be decorated like this:

```python
@pytest.mark.integration
def test_something_requiring_redis_running():
  pass
```

Running the tests with `pytest -m"integration"` will run *only* integration tests while `pytest -m"not integration"` will run whatever was not marked as an integration test.

The second matrix is defined with `tox` like this:

```ini
envlist = unit, redis{32,40}, flake8

...

[testenv:redis32]
setenv = REDIS_VERSION=3.2
...

[testenv:redis40]
setenv = REDIS_VERSION=4.0
...
```

### Integration tests

Redis instances are orchestrated with `docker-compose` which is now a dependency
to run the integration tests. It's `pytest` responsible to start/stop/dispose an
instance using the `fixture` concept.

This is how a fixture orchestrating Redis instances looks like:

```python
@pytest.fixture(scope="session")
def redis_auth():
    # omitted `docker compose` invokation setup here ...
    subprocess.check_call(args + ["up", "-d"], env=env)
    yield
    subprocess.check_call(args + ["down"], env=env)
```

the basic concept is that `docker compose up` is run right after the fixture
is made available to the test function (it blocks on `yield`). When the test
has done, `yield` unblocks and `docker compose down` is called. Notice the
`scope=session` argument passed to the fixture decorator, it allows the
`yield` to block only once for **all the tests** , unblocking only after the
last test: this is useful to avoid having `docker compose up` and `down`
called at every test. One caveat with this approach is that if you have data
in Redis, some test might operate on a dirty database - this is not an issue
in this case but something to keep in mind when using `scope=session`.

### Running the tests locally

**Note**: you need `docker` and `docker-compose` to be installed on your system
in order to run the tests locally.

During development, tests can be locally run with tox, same as in the CI. In the case of Redis, there might be no need to test the whole matrix all the times, so for example if you want to run only the unit/mocked tests:

```shell
tox -e unit
```

if you want to run integration tests but against one Redis version only:

```shell
tox -e redis40
```

tox is great because it creates a virtual Python environment for each tox env but if you don't need this level of isolation you can speed up the development iterations using `pytest` directly (which is what tox does under the hood):

```shell
REDIS_VERSION=4.0 pytest
```

or if you don't want to run integration tests:

```shell
pytest -m"not integration"
```
