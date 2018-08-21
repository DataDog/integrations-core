# Package checks as Python wheels
- Authors: Massimiliano Pippi
- Date: 2017-06-08
- Discussion: https://github.com/DataDog/integrations-core/pull/634
- Status: accepted

## Overview

Checks were originally part of the Agent codebase and were created as single
Python modules, programmatically imported using the name of the check (that must
coincide with the name of the module) and the path to the folder containing the
source file. See https://github.com/DataDog/dd-agent/blob/5.14.x/config.py#L830.

When checks were moved in a separate repo to implement the concept of
"Integrations SDK", to minimize the work on the Agent while still support this
new way of distributing checks, the same logic was kept and now such Python
modules are allowed to live in a different directory.

## Problem

At the moment, the Agent package contains all the checks marked as "core" and
officially maintained by Datadog, available at https://github.com/DataDog/integrations-core.
After being decoupled from the Agent, a check can now be installed as a separate
package and picked up by the Agent at runtime, taking precedence over the one
shipped with the agent package.

To allow users to easily add a more recent version of a check in this fashion,
checks need to be built, packaged and distributed individually, and currently
this happens using the same strategies as the Agent package: we use Omnibus to
create packages for the supported operating systems (.deb, .rpm, Windows
installer).

The current implementation of Integrations SDK exposes the Agent to a set of
different problems, part of them are legacy and were already present in the
Agent before moving out the checks but part of them were introduced in the
process of implementing the SDK, let's see few examples.


### Building

At this moment, if contributors want to build a patched version of a check to
use within their infrastructure, they have to either replicate our own build
pipeline or create their own. The latter is way simpler than the former but when
choosing this path you're basically alone, being able to reuse very little code
and tools from the agent codebase which is strongly focused on supporting our
own build pipeline. This also affects the development process: since a check is
not meant to live without an agent, the only way you have to test a modified
version of a check is build a package on your own or manually patch an installed
agent - both strategies carry on a long list of issues.

### Versioning

Despite having separated the checks from the agent, the two codebases are still
strongly coupled when it comes to versioning. Checks are supposed to be released in standalone mode, without a corresponding agent release, and in a manual fashion: we decide when a new release for a check is needed and we trigger the release process. This means we might have changes piling up on `master` between one release and another which is fine but doesn't play well when an agent
release falls in the middle: when we release the agent, we embed all the checks
we find on `master` in `integrations-core`, leaving the check in an inconsistent
state: "not released as standalone but released with an agent". A workaround to
this would be forcing a standalone release for all the checks in `integrations-core`
when we release an agent, (a fix is in place starting with 5.15) but the
process is time consuming and not straightforward.

### Dependencies

Same as for versioning, strong coupling between Agent and checks is an issue
from a dependencies management standpoint. At the moment, each check lists the
packages and the versions it needs in a requirements file that we manually
process during the build of the agent. In other words, we let the check list the
dependencies but we implement the logic elsewhere.

### User experience: final user

At the moment we are exposed to weird corner cases when it comes to the point of
installing checks in standalone mode, let's see an example:

 * User installs agent 5.0.0 shipping ntp check 1.0.0
 * Agent 5.1.0 gets released, shipping ntp check 1.1.0
 * User updates **only** the ntp check to 1.1.0
 * Agent 5.2.0 gets released, shipping ntp check 1.2.0
 * User updates the agent to 5.2.0 but still runs ntp 1.1.0 (standalone checks
 take precedence)

We have strategies in place to mitigate the effect of the example above, but the
problem still exists.

### User experience: developer

Most of the checks are supposed to run both unit and integration tests, at the
moment they are merged in a single test file run by our CI. A contributor needs
to use our ruby-based tooling in order to run tests, even in the case they only
want to run unit tests.

Most if not all the checks are not supposed to run outside the agent lifecycle,
working on a brand new check or trying to change an existing one heavily rely on
this, making things more complicated than they could be.

A couple of related, minor issues it would be nice to fix: at the moment it's not
possible to split the code of a check across multiple Python modules, same
happens for the tests.

## Constraints

Any solution must work with the new agent, working for both the old and the new
one is preferable.

## Recommended Solution

### Package checks as Python Wheels

The solution proposed is to migrate packaging and distribution for checks in
`integrations-core` and `integrations-extra` from system packages built with
Omnibus to _universal Python Wheels_ when possible, and _binary Wheels_ when
we need to ship non-python artifacts.

The changes needed in the agent to support this additional method of checks
distribution are the following:
https://github.com/DataDog/dd-agent/compare/massi/whl-poc
The proof of concept should be extended to rework a bit the loading logic but
it already works.

The work needed to migrate a pure Python check to wheels is not that much, see
the ntp check for an example:
https://github.com/DataDog/integrations-core/tree/massi/whl-poc/ntp

The ability of the agent to progammatically import and run a single Python
module from a well known path in the filesystem will be preserved, so that
we don't break any custom check in the wild.

Moving to wheels wouldn't solve any possible problem we're facing in building
and shipping `integrations-core` and `integrations-extra` but overall it might
work better, let's see few examples.

#### Building

Building a pure Python check would be as easy as doing
`python setup.py bdist_wheel`. In the case of checks that ship binary artifacts
more work would be needed to set up the build scripts, still the build strategy
would be the same. A locally built check is basically a zip archive, so it could
be easily moved around and picked up by an agent. In the case of a pure python
check, the archives would be platform independent, meaning one could build the
check on a Mac and copy and install the artifact in a Linux box.

#### Versioning

This is not strongly related to the wheel packaging system, but the overall
philosophy of decoupling the checks from the agent that comes with the wheels
might help with versioning. Each check would have its own release cycle and at
each agent release we would pick and include in the package the desired version
of each check in integrations-core by invoking `pip install -r` on a special
requirements.txt file that would be part of the agent repository. That file
would likely contain the most recent version of each check wheel package but
this wouldn't be enforced, what it counts is that the requirements file would be
the unique source of truth stating which checks are shipped with which agent.

#### Dependencies

We would leverage Python integrated tools to keep dependencies sane.
For example, pip would refuse to downgrade a check if this breaks the
dependencies for another check. See the Upgrade paragraph for what should happen
at every agent upgrade.

We could also provide a dummy Agent wheel package integrations would depend on:
this would enforce compatibility with the core agent at install time (enforced
by pip) instead of at runtime (enforced by the gent itself after reading check
metadata). This would also make manifest files unnecessary since we would use
setuptools to handle package metadata.

#### Distribution

Datadog would distribute wheel packages for integrations-core and integrations-extra
through their own Python Package Repositories. Bare minimal version would be a
file server available through HTTPS (S3+cloudfront for example): if we use the
CI to upload the wheel packages and take care of filesystem structure,
that would be enough to implement a distribution channel.

If we want to leverage distutils capabilities, included commands like `setup upload`
and provide a full fledged PyPi-like website where people can browse package
metadata, we need to install specific software (open source or cloud hosted
projects implementing it).

Being the two repos separated, we could grant checks maintainers push rights on
the integrations-extra repo and let the CI build and upload the package to the
PyPi channel dedicated to extra.

Any tool supporting the development process for the checks will go in the
official PyPi repository instead. For example, the Python package replicating
the functionalities that actually live in the agent could be pip installable
from pypi.org directly, without forcing contributors to install the full
agent package on their laptop.

#### Upgrade path
_Note: this will affect the "end user" experience._

##### Recommended solution: nuke core dependencies, keep custom checks

We can wrap pip execution in the agent command line so that when users install a
custom check, pip is actually invoked whit this parameter:
`--target=/opt/datadog-agent/sdk package_name`

Pros:
 * Custom checks are still there after an upgrade, whether they were added with
 the old strategy (python module copied over /etc/dd-agent/checks.d/) or through
 pip.

Cons:
 * Users wouldn't be able to pin specific check versions (this could be a non
 requirement)

Errors might still happen at runtime if a custom check relies on a dependency
that was updated along with the agent upgrade (not sure there's a fix for this).

##### Alternative solution 1: nuke allthethings

We consider the core checks as "part of the embedded Python standard library".
At every Agent upgrade, the list of Python packages installed in the embedded
interpreter would be reset.

Pros:
 * Easier to maintain
 * After every upgrade the Agent would be in a well known state

Cons:
 * Custom checks implemented as wheels would be wiped and users should add them
 back (this doesn't affect custom checks installed with the old method)
 * Pinned versions of core checks would be overwritten by newer ones (again, this
 might be a non requirement)

##### Alternative solution 2: preserve the existing Python environment

We assume the Agent can run with any Python environment

Pros:
 * If users pin a package (custom or core) it would be still there after an
 agent upgrade

Cons:
 * Check should be installed during a post install step of the Agent, this way
 we delegate to pip the responsibility of trying to keep the pinned versions.
 This might error in so many ways that this strategy could be considered a no go.

#### User experience: end user

Again, we would leverage python internal tools to improve user experience.
Datadog would provide wheel packages through an official and verified
distribution channel (see above paragraph) so that the installation of a new
check would be:

`sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install datadog.check.ntp-1.1.0-py2-none-any.whl`

The command would look like the same in any platform and (as stated before) we
could add wrappers to the agent command line for the install/update procedures:

`datadog-agent install datadog.check.ntp-1.1.0-py2-none-any.whl`

or even:

`datadog-agent install --index-url python.mycompany.org ntp`

#### User experience: developer

Eventually the developer user experience would be really Pythonic, in the sense
that working on a check wouldn't be that different from working on any other
python project: same tools, same concepts. Along with the new packaging it would
come the opportunity to split the code across multiple files in the same package,
easily run unit tests locally, the ability to build and install a custom version
of the check easily and a-la-python, the ability to run the check locally
without an agent running, just for the sake of testing out how the code works.

### Open Questions

#### Agent5 vs Agent6 support

The POC was based on Agent5 with good results. To implement agent decoupling, a
Python package was created to provide common code and testing facilities when
the actual agent is missing, see:
https://github.com/DataDog/dd-agent/blob/massi/whl-poc/setup.py
When a user needs to work on a check, the only prerequisite is to have this
package installed, then tests will work as the agent was there.

This is not applicable to Agent6, since the `aggregator` Python module only
exists in memory when the Go agent is running the embedded Python. We can
provide a mocked `aggregator` but tests wouldn't be reliable with the current
testing approach. The solution to this would be to slightly change our tests so
that instead of simulating a complete collection cycle and see what arrives
to the forwarder, we invoke the `check` method and look what arrives to the the
(mocked at this point) `aggregator`.

Integration tests should be adjusted as well.

### Appendix

Wheels documentation: https://packaging.python.org/tutorials/distributing-packages/#wheels

