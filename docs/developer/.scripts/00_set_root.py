import os

from datadog_checks.dev.tooling.constants import get_root, set_root


def patch(lines):
    """This ensures the root directory is set for subsequent scripts using ddev tooling."""
    if not get_root():
        set_root(os.getcwd())
