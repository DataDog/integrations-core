# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from click.testing import CliRunner

from datadog_checks.dev.tooling.commands.validate.agent_reqs import agent_reqs
from datadog_checks.dev.tooling.constants import get_root, set_root


def test_validate_agent_reqs_fails_on_stale_release_entry():
    runner = CliRunner()
    previous_root = get_root()

    try:
        with runner.isolated_filesystem():
            set_root(os.getcwd())
            write_check('foo', '1.0.0')
            with open('requirements-agent-release.txt', 'w', encoding='utf-8') as f:
                f.write('# DO NOT PASS THIS TO PIP DIRECTLY\ndatadog-foo==1.0.0\ndatadog-snowflake==7.13.0\n')

            result = runner.invoke(agent_reqs)

            assert result.exit_code == 1
            assert (
                'datadog-snowflake is pinned in requirements-agent-release.txt '
                'but `snowflake` is not present in the repo'
            ) in result.output
    finally:
        set_root(previous_root)


def write_check(name: str, version: str) -> None:
    """Create the minimum check structure needed by agent-reqs."""
    check_package = os.path.join(name, 'datadog_checks', name)
    os.makedirs(check_package)
    with open(os.path.join(check_package, '__about__.py'), 'w', encoding='utf-8') as f:
        f.write(f'__version__ = "{version}"\n')
