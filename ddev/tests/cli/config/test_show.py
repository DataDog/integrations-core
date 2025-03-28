# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.config.file import ConfigFileWithOverrides
from ddev.utils.fs import Path

CORE_PATH = Path("~") / "dd" / "integrations-core"
EXTRAS_PATH = Path("~") / "dd" / "integrations-extras"
MARKETPLACE_PATH = Path("~") / "dd" / "marketplace"
AGENT_PATH = Path("~") / "dd" / "datadog-agent"

EXPECTED_SCRUBBED_OUTPUT = f"""
repo = "core"
agent = "dev"
org = "default"

[repos]
core = "{CORE_PATH}"
extras = "{EXTRAS_PATH}"
marketplace = "{MARKETPLACE_PATH}"
agent = "{AGENT_PATH}"

[agents.dev]
docker = "datadog/agent-dev:master"
local = "latest"

[agents.7]
docker = "datadog/agent:7"
local = "7"

[orgs.default]
api_key = "*****"
app_key = "*****"
site = "datadoghq.com"
dd_url = "https://app.datadoghq.com"
log_url = ""

[github]
user = ""
token = "*****"

[pypi]
user = ""
auth = "*****"

[trello]
key = ""
token = "*****"

[terminal.styles]
info = "bold"
success = "bold cyan"
error = "bold red"
warning = "bold yellow"
waiting = "bold magenta"
debug = "bold"
spinner = "simpleDotsScrolling"
"""

EXPECTED_NON_SCRUBBED_OUTPUT = f"""
repo = "core"
agent = "dev"
org = "default"

[repos]
core = "{CORE_PATH}"
extras = "{EXTRAS_PATH}"
marketplace = "{MARKETPLACE_PATH}"
agent = "{AGENT_PATH}"

[agents.dev]
docker = "datadog/agent-dev:master"
local = "latest"

[agents.7]
docker = "datadog/agent:7"
local = "7"

[orgs.default]
api_key = "foo"
app_key = "bar"
site = "datadoghq.com"
dd_url = "https://app.datadoghq.com"
log_url = ""

[github]
user = ""
token = ""

[pypi]
user = ""
auth = ""

[trello]
key = ""
token = ""

[terminal.styles]
info = "bold"
success = "bold cyan"
error = "bold red"
warning = "bold yellow"
waiting = "bold magenta"
debug = "bold"
spinner = "simpleDotsScrolling"
"""


@pytest.fixture(autouse=True)
def valid_config_file(config_file):
    config_file.restore()
    config_file.model.orgs['default']['api_key'] = 'foo'
    config_file.model.orgs['default']['app_key'] = 'bar'
    config_file.model.github = {'user': '', 'token': ''}
    config_file.save()


@pytest.mark.parametrize(
    "command,expected",
    [
        (["config", "show"], EXPECTED_SCRUBBED_OUTPUT),
        (["config", "show", "-a"], EXPECTED_NON_SCRUBBED_OUTPUT),
    ],
    ids=["scrubbed", "non_scrubbed"],
)
def test_default_scrubbed(ddev, helpers, command, expected):
    result = ddev(*command)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(expected.replace('\\', '\\\\'))


def build_expected_output_with_line_sources(expected: str, config_file: ConfigFileWithOverrides) -> str:
    # Need to replace backslashes for double ones as that is what will be used to measure line length
    # when reading from a file.
    expected_lines = expected.replace('\\', '\\\\').splitlines()
    line_sources = {
        0: 'config.toml:1',
        1: 'config.toml:2',
        2: 'config.toml:3',
        # Blank line
        4: 'config.toml:5',
        5: 'config.toml:6',
        6: 'config.toml:7',
        7: 'config.toml:8',
        8: 'config.toml:9',
        # Blank line
        10: 'config.toml:11',
        11: 'config.toml:12',
        12: 'config.toml:13',
        # Blank line
        14: 'config.toml:15',
        15: 'config.toml:16',
        16: 'config.toml:17',
        # Blank line
        18: '.ddev.toml:1',
        19: '.ddev.toml:2',
        20: 'config.toml:21',
        21: 'config.toml:22',
        22: 'config.toml:23',
        23: 'config.toml:24',
        # Blank line
        25: 'config.toml:26',
        26: 'config.toml:27',
        27: 'config.toml:28',
        # Blank line
        29: 'config.toml:30',
        30: 'config.toml:31',
        31: 'config.toml:32',
        # Blank line
        33: 'config.toml:34',
        34: 'config.toml:35',
        35: 'config.toml:36',
        # Blank line
        37: 'config.toml:38',
        38: 'config.toml:39',
        39: 'config.toml:40',
        40: 'config.toml:41',
        41: 'config.toml:42',
        42: 'config.toml:43',
        43: 'config.toml:44',
        44: 'config.toml:45',
    }

    # Add a blank line at the end to match the expected output
    return config_file._build_read_string(expected_lines, line_sources) + "\n"


@pytest.mark.parametrize(
    "command,expected",
    [
        (["config", "show"], EXPECTED_SCRUBBED_OUTPUT),
        (["config", "show", "-a"], EXPECTED_NON_SCRUBBED_OUTPUT),
    ],
    ids=["scrubbed", "non_scrubbed"],
)
def test_show_with_local_overrides(ddev, config_file, helpers, command, expected):
    # Create local config with overrides
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )

    config_file.local_path.write_text(local_config)

    result = ddev(*command)

    assert result.exit_code == 0, result.output
    expected_with_local_overrides = expected.replace('api_key = "foo"', 'api_key = "local_foo"')
    expected_output = build_expected_output_with_line_sources(
        helpers.dedent(expected_with_local_overrides), config_file
    )
    assert result.output == expected_output


def test_verbose_output_without_local_file(ddev):
    """Test that verbose output does not show local override message when no local file exists."""
    result = ddev("-v", "config", "show")
    assert result.exit_code == 0
    assert "Local override config file found" not in result.output


def test_verbose_output_with_local_file(ddev, config_file, helpers):
    """Test that verbose output shows local override message when local file exists."""
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )
    config_file.local_path.write_text(local_config)

    result = ddev("-v", "config", "show")
    assert result.exit_code == 0
    assert "Local override config file found" in result.output

    # Clean up
    config_file.local_path.unlink()
