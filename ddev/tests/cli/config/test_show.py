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
        0: 'GlobalConfig:1',
        1: 'GlobalConfig:2',
        2: 'GlobalConfig:3',
        # Blank line
        4: 'GlobalConfig:5',
        5: 'GlobalConfig:6',
        6: 'GlobalConfig:7',
        7: 'GlobalConfig:8',
        8: 'GlobalConfig:9',
        # Blank line
        10: 'GlobalConfig:11',
        11: 'GlobalConfig:12',
        12: 'GlobalConfig:13',
        # Blank line
        14: 'GlobalConfig:15',
        15: 'GlobalConfig:16',
        16: 'GlobalConfig:17',
        # Blank line
        18: 'Overrides:1',
        19: 'Overrides:2',
        20: 'GlobalConfig:21',
        21: 'GlobalConfig:22',
        22: 'GlobalConfig:23',
        23: 'GlobalConfig:24',
        # Blank line
        25: 'GlobalConfig:26',
        26: 'GlobalConfig:27',
        27: 'GlobalConfig:28',
        # Blank line
        29: 'GlobalConfig:30',
        30: 'GlobalConfig:31',
        31: 'GlobalConfig:32',
        # Blank line
        33: 'GlobalConfig:34',
        34: 'GlobalConfig:35',
        35: 'GlobalConfig:36',
        # Blank line
        37: 'GlobalConfig:38',
        38: 'GlobalConfig:39',
        39: 'GlobalConfig:40',
        40: 'GlobalConfig:41',
        41: 'GlobalConfig:42',
        42: 'GlobalConfig:43',
        43: 'GlobalConfig:44',
        44: 'GlobalConfig:45',
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
def test_show_with_local_overrides(ddev, config_file, helpers, command, expected, overrides_config):
    # Create local config with overrides
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )

    overrides_config.write_text(local_config)

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


def test_verbose_output_with_local_file(ddev, config_file, helpers, overrides_config):
    """Test that verbose output shows local override message when local file exists."""
    local_config = helpers.dedent(
        """
        [orgs.default]
        api_key = "local_foo"
        """
    )
    overrides_config.write_text(local_config)

    result = ddev("-v", "config", "show")
    assert result.exit_code == 0
    assert "Local override config file found" in result.output
