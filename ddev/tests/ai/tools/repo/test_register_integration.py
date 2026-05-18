# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from textwrap import dedent

import pytest
import tomlkit

from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.repo.register_integration import RegisterIntegrationTool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEED_TOML = dedent(
    """\
    # Repo-wide validations.
    validations = ["agent-reqs"]

    [overrides.display-name]
    existing_integration = "Existing Integration"

    [overrides.metrics-prefix]
    existing_integration = "existing."

    # Use manifest-like platforms
    [overrides.manifest.platforms]
    existing_integration = ["linux", "windows", "mac_os"]
    """
)


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """tmp_path-rooted repo containing a seeded .ddev/config.toml."""
    (tmp_path / ".ddev").mkdir()
    (tmp_path / ".ddev" / "config.toml").write_text(SEED_TOML, encoding="utf-8")
    return tmp_path


def _build_tool(repo_root: Path, integration: str) -> RegisterIntegrationTool:
    """Builds a tool whose write_root's basename is the integration name."""
    write_root = repo_root / integration
    write_root.mkdir(parents=True, exist_ok=True)
    return RegisterIntegrationTool(FileAccessPolicy(write_root=write_root))


@pytest.fixture
def tool(repo_root: Path) -> RegisterIntegrationTool:
    """Tool for a fresh integration named 'kuma'."""
    return _build_tool(repo_root, "kuma")


@pytest.fixture
def existing_tool(repo_root: Path) -> RegisterIntegrationTool:
    """Tool for the already-registered 'existing_integration'."""
    return _build_tool(repo_root, "existing_integration")


def _read_config(repo_root: Path) -> dict:
    return tomlkit.parse((repo_root / ".ddev" / "config.toml").read_text(encoding="utf-8"))


def _platforms_for(doc, integration: str):
    return doc["overrides"]["manifest"]["platforms"].get(integration)


def _display_name_for(doc, integration: str):
    return doc["overrides"]["display-name"].get(integration)


def _metrics_prefix_for(doc, integration: str):
    return doc["overrides"]["metrics-prefix"].get(integration)


# ---------------------------------------------------------------------------
# Mandatory-only and optional combinations on a fresh integration
# ---------------------------------------------------------------------------


async def test_registers_only_manifest_platforms_when_no_optionals(tool, repo_root):
    result = await tool.run({"platforms": ["linux"]})

    assert result.success is True
    doc = _read_config(repo_root)
    assert _platforms_for(doc, "kuma") == ["linux"]
    assert _display_name_for(doc, "kuma") is None
    assert _metrics_prefix_for(doc, "kuma") is None


async def test_writes_display_name_when_supplied(tool, repo_root):
    result = await tool.run({"platforms": ["linux"], "display_name": "Kuma Mesh"})

    assert result.success is True
    doc = _read_config(repo_root)
    assert _display_name_for(doc, "kuma") == "Kuma Mesh"
    assert _metrics_prefix_for(doc, "kuma") is None


async def test_writes_metrics_prefix_when_supplied(tool, repo_root):
    result = await tool.run({"platforms": ["linux"], "metrics_prefix": "kuma."})

    assert result.success is True
    doc = _read_config(repo_root)
    assert _metrics_prefix_for(doc, "kuma") == "kuma."
    assert _display_name_for(doc, "kuma") is None


async def test_writes_all_three_when_both_optionals_supplied(tool, repo_root):
    result = await tool.run(
        {
            "platforms": ["linux", "windows"],
            "display_name": "Kuma Mesh",
            "metrics_prefix": "kuma.",
        }
    )

    assert result.success is True
    doc = _read_config(repo_root)
    assert _platforms_for(doc, "kuma") == ["linux", "windows"]
    assert _display_name_for(doc, "kuma") == "Kuma Mesh"
    assert _metrics_prefix_for(doc, "kuma") == "kuma."


# ---------------------------------------------------------------------------
# Integration name derives from write_root
# ---------------------------------------------------------------------------


async def test_integration_name_taken_from_write_root_basename(repo_root):
    """Naming the write_root 'foo_bar' registers 'foo_bar' — not any other name."""
    tool = _build_tool(repo_root, "foo_bar")

    result = await tool.run({"platforms": ["linux"]})

    assert result.success is True
    doc = _read_config(repo_root)
    assert _platforms_for(doc, "foo_bar") == ["linux"]
    assert _platforms_for(doc, "kuma") is None


# ---------------------------------------------------------------------------
# Preservation: pre-existing entries and comments survive
# ---------------------------------------------------------------------------


async def test_preserves_unrelated_entries_in_every_section(tool, repo_root):
    await tool.run(
        {
            "platforms": ["linux"],
            "display_name": "Kuma",
            "metrics_prefix": "kuma.",
        }
    )

    doc = _read_config(repo_root)
    assert _platforms_for(doc, "existing_integration") == ["linux", "windows", "mac_os"]
    assert _display_name_for(doc, "existing_integration") == "Existing Integration"
    assert _metrics_prefix_for(doc, "existing_integration") == "existing."


async def test_preserves_comments(tool, repo_root):
    await tool.run({"platforms": ["linux"]})

    raw = (repo_root / ".ddev" / "config.toml").read_text(encoding="utf-8")
    assert "# Repo-wide validations." in raw
    assert "# Use manifest-like platforms" in raw


# ---------------------------------------------------------------------------
# Idempotency: re-registering with the SAME values is a noop success
# ---------------------------------------------------------------------------


async def test_idempotent_same_platforms_returns_success_without_changes(existing_tool, repo_root):
    """Re-running with platforms matching the existing entry returns success and does not rewrite."""
    original_bytes = (repo_root / ".ddev" / "config.toml").read_bytes()

    result = await existing_tool.run({"platforms": ["linux", "windows", "mac_os"]})

    assert result.success is True
    assert (repo_root / ".ddev" / "config.toml").read_bytes() == original_bytes


async def test_idempotent_same_display_name(repo_root):
    """If only display_name was previously set, re-supplying matches and noops."""
    config_path = repo_root / ".ddev" / "config.toml"
    doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    del doc["overrides"]["manifest"]["platforms"]["existing_integration"]
    del doc["overrides"]["metrics-prefix"]["existing_integration"]
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    tool = _build_tool(repo_root, "existing_integration")
    result = await tool.run({"platforms": ["linux"], "display_name": "Existing Integration"})

    assert result.success is True
    parsed = _read_config(repo_root)
    assert _display_name_for(parsed, "existing_integration") == "Existing Integration"
    assert _platforms_for(parsed, "existing_integration") == ["linux"]


# ---------------------------------------------------------------------------
# Mismatch: re-registering with a DIFFERENT value fails loudly
# ---------------------------------------------------------------------------


async def test_mismatch_on_platforms_fails_with_diff_in_error(existing_tool, repo_root):
    result = await existing_tool.run({"platforms": ["linux"]})

    assert result.success is False
    assert "manifest.platforms" in result.error
    assert "['linux']" in result.error
    assert "linux" in result.error and "windows" in result.error and "mac_os" in result.error

    doc = _read_config(repo_root)
    assert _platforms_for(doc, "existing_integration") == ["linux", "windows", "mac_os"]


async def test_mismatch_on_display_name_fails(repo_root):
    config_path = repo_root / ".ddev" / "config.toml"
    doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    del doc["overrides"]["manifest"]["platforms"]["existing_integration"]
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    tool = _build_tool(repo_root, "existing_integration")
    result = await tool.run(
        {
            "platforms": ["linux"],
            "display_name": "Something Different",
        }
    )

    assert result.success is False
    assert "display-name" in result.error
    assert "Something Different" in result.error
    assert "Existing Integration" in result.error


async def test_mismatch_on_metrics_prefix_fails(repo_root):
    config_path = repo_root / ".ddev" / "config.toml"
    doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    del doc["overrides"]["manifest"]["platforms"]["existing_integration"]
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    tool = _build_tool(repo_root, "existing_integration")
    result = await tool.run(
        {
            "platforms": ["linux"],
            "metrics_prefix": "different.",
        }
    )

    assert result.success is False
    assert "metrics-prefix" in result.error
    assert "different." in result.error
    assert "existing." in result.error


async def test_mismatch_leaves_other_sections_untouched(existing_tool, repo_root):
    """A mismatch on the mandatory section must not partially-write the optionals."""
    await existing_tool.run(
        {
            "platforms": ["linux"],
            "display_name": "Should Not Apply",
            "metrics_prefix": "should_not_apply.",
        }
    )

    doc = _read_config(repo_root)
    assert _display_name_for(doc, "existing_integration") == "Existing Integration"
    assert _metrics_prefix_for(doc, "existing_integration") == "existing."
    assert _platforms_for(doc, "existing_integration") == ["linux", "windows", "mac_os"]


# ---------------------------------------------------------------------------
# Locating .ddev/config.toml
# ---------------------------------------------------------------------------


async def test_missing_config_returns_failure(tmp_path):
    """No .ddev/config.toml anywhere walking up — clear failure."""
    write_root = tmp_path / "scratch" / "kuma"
    write_root.mkdir(parents=True)
    tool = RegisterIntegrationTool(FileAccessPolicy(write_root=write_root))

    result = await tool.run({"platforms": ["linux"]})

    assert result.success is False
    assert result.error is not None


async def test_walks_up_to_find_config(repo_root):
    """write_root nested several levels below repo root still resolves the config."""
    deep = repo_root / "a" / "b" / "kuma"
    deep.mkdir(parents=True)
    tool = RegisterIntegrationTool(FileAccessPolicy(write_root=deep))

    result = await tool.run({"platforms": ["linux"]})

    assert result.success is True
    doc = _read_config(repo_root)
    assert _platforms_for(doc, "kuma") == ["linux"]


# ---------------------------------------------------------------------------
# Platform list ordering survives the round-trip on a write
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "platforms",
    [
        ["linux"],
        ["windows"],
        ["mac_os"],
        ["linux", "windows"],
        ["windows", "linux"],
        ["linux", "windows", "mac_os"],
        ["mac_os", "linux", "windows"],
    ],
)
async def test_platform_list_ordering_preserved(repo_root, platforms):
    tool = _build_tool(repo_root, "kuma")
    result = await tool.run({"platforms": platforms})

    assert result.success is True
    doc = _read_config(repo_root)
    assert list(_platforms_for(doc, "kuma")) == platforms
