# ddev Test Guidelines

These conventions apply to the tests under `ddev/tests/`. They supplement the repository root
`AGENTS.md`; where they overlap, the root file still applies.

## Importing from `conftest.py`

**Runtime rule: nothing imports from a `conftest.py` at runtime.** Pytest loads
conftest files through its own plugin machinery; importing one as a regular
module can create a second copy, double-registering fixtures and duplicating
module state. It may work in today's layout; it breaks under
`--import-mode=importlib`.

**The one exception: fixture types.** A type that describes what a fixture
returns (e.g. a Protocol for a factory fixture's callable) lives next to that
fixture in `conftest.py`, so the fixture itself is typed where it is defined.
Tests that need it for annotations import it under `if TYPE_CHECKING:` only:

    # conftest.py
    class ClientFactory(Protocol):
        def __call__(self, transport: httpx.MockTransport) -> AsyncGitHubClient: ...

    @pytest.fixture
    def client_factory(...) -> ClientFactory: ...

    # test_x.py
    if TYPE_CHECKING:
        from .conftest import ClientFactory

    def test_y(client_factory: ClientFactory) -> None: ...

The guard is what makes this safe: the import never runs, so no second module
is created. A conftest import outside `if TYPE_CHECKING:` is a bug, and a
`TYPE_CHECKING` import of anything other than types (helpers, constants,
payload factories) is too — needing one of those at runtime means it belongs
in a helpers module.

## Shared test code: scopes and placement

Helpers live at the narrowest scope that contains all their users. Three scopes
exist, from narrowest to broadest:

| Scope     | Location                                   | Who may use it                          |
|-----------|--------------------------------------------|------------------------------------------|
| Local     | `helpers.py` next to the tests             | Tests in that one package                |
| Subtree   | `helpers/` package at a subtree root (e.g. `tests/x/mypackage/helpers/`) | Test packages anywhere under that subtree |
| Global    | `tests/helpers/`                            | Any test suite                           |

Module vs package is size, not meaning: a `helpers.py` that outgrows one file
becomes a `helpers/` package with the public names re-exported from
`__init__.py`, and its scope does not change by doing so.

**Placement rules:**

- A new helper starts local. When a second package under the same subtree needs
  it, promote it to the subtree `helpers/`. When packages outside the subtree
  need it, promote it to `tests/helpers/`. Promote, never copy.
- Imports point upward only: tests and local helpers may import from their
  subtree helpers and from `tests/helpers/`; subtree helpers may import from
  `tests/helpers/`. Never import sideways from another package's local
  `helpers.py` — a sideways import means the helper's scope is wrong; promote it.
- `conftest.py` at any level may import from helpers at its level or above.
  Helpers never import from any conftest (see the conftest section).
- Helpers contain no fixtures. Anything decorated with `@pytest.fixture`
  belongs in a `conftest.py`; helpers hold the plain functions, factories,
  transports, registries, and types those fixtures and tests build on.

Litmus test when adding a helper: list who uses it today, find their nearest
common ancestor in the tree, and put it there. If you cannot name a second
user, it is local.
