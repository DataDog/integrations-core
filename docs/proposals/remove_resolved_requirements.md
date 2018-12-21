# Removing requirements.txt
- Authors: Ofek Lev
- Date: 2018-12-20
- Discussion: https://github.com/DataDog/integrations-core/pull/2800
- Status: accepted

## Origin

At the start, there was only one dependency file: `requirements.txt`. It was used exclusively for our Ruby/rake tests. The contents appear to have come directly from the `dd-agent` and omnibus repos during the:

- Migration of checks to their own repo (integrations-core), e.g. https://github.com/DataDog/integrations-core/pull/50
- Porting of checks to wheels https://github.com/DataDog/integrations-core/pull/829

## Port to wheels

During the effort to make every check its own Python package, it was also decided that, to further the separation of the agents and their integrations, the builders should install each check as a wheel, thus setting up the scaffolding to move to using every check’s defined dependency file rather than a single large file of dependencies. See:

- https://github.com/DataDog/dd-agent-omnibus/pull/213
- https://github.com/DataDog/datadog-agent/pull/1048

## New testing framework

During review of the PoC for tox/pytest, security asked us to define what is required and then resolve the dependencies in a separate file to ease use of security scanners and improve security when installing the wheels. The pinned file became `requirements.in` and the resolved file became `requirements.txt`. See https://github.com/DataDog/integrations-core/pull/1024#discussion_r162973079

The work to unpack each wheel to verify dependency hashes had not been done yet (and never was) so we began by using `requirements.in` in every `setup.py`.

## Static environment

### Installation of wheels

During testing of our new wheel pipeline it was discovered that, since wheels were built with `requirements.in` as `install_requires`, installation had the potential to break other checks’ compatibility. We therefore removed dependencies from `setup.py` and used `requirements.in` in the builders. See:

- https://github.com/DataDog/integrations-core/pull/1796
- https://github.com/DataDog/datadog-agent/pull/1896

### Dependency conflicts

We began running into issues where the builders would fail because, since pip has no resolver, transient dependencies from one package would be incompatible with others. To remedy this we began catching conflicts in our CI, syncing every dependency to one static file (agent_requirements.in), and resolving the static file locally and committing the resulting file (agent_requirements.txt). See:

- https://github.com/DataDog/integrations-core/pull/1760

### Cross-platform support

We discovered shortly before an agent release that this strategy did not work because some dependencies that are platform-specific would either be missing or fail to install depending on which machine the committer happened to be on when resolving. To fix this we introduced environment markers and began resolving `agent_requirements.in` on the builders. See:

- https://github.com/DataDog/integrations-core/pull/1921
- https://github.com/DataDog/dd-agent-omnibus/pull/268

## Why they are being removed

They are not being used anywhere now except tox and we’re facing cross-platform issues due to environment markers in `requirements.in` often forcing us to manually edit `requirements.txt`.
