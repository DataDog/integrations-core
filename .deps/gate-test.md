Throwaway file used to smoke-test the dependency-wheel-promotion gate notice.

It lives under `.deps/` so the gate treats the PR as changing dependencies, but
`.deps/` is not one of the resolution inputs in `.builders/inputs_hash.py`, so no
wheel rebuild is triggered. Delete this file and close the PR once the notice has
been checked.
