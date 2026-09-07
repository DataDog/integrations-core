# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import pytest

from ddev.cli.ci.tests.batching.exceptions import PlanningError
from ddev.cli.ci.tests.batching.hatch_environments import HatchEnvironmentProvider
from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig
from ddev.utils.fs import Path as DdevPath
from ddev.utils.platform import PlatformName


def integration_with_config(tmp_path: Path, content: str) -> Integration:
    path = DdevPath(tmp_path, "sample")
    path.mkdir()
    (path / "hatch.toml").write_text(dedent(content), encoding="utf-8")
    return Integration(path, DdevPath(tmp_path), RepositoryConfig(DdevPath(tmp_path, "config.toml")))


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        pytest.param('[envs.default]\npython = "3.11"', [("default", "3.11")], id="default-only"),
        pytest.param('[envs.default]', [("default", "3.13")], id="default-python"),
        pytest.param(
            '''
            [envs.default]
            python = "3.12"
            [[envs.default.matrix]]
            version = ["1", "2"]
            ''',
            [("1", "3.12"), ("2", "3.12")],
            id="python-outside-matrix",
        ),
        pytest.param(
            '''
            [[envs.default.matrix]]
            version = ["9", "10"]
            python = ["3.11", "3.13"]
            [[envs.default.matrix]]
            python = ["3.13"]
            version = ["9"]
            setup = ["cluster"]
            [envs.default.overrides]
            matrix.version.env-vars = "VERSION"
            GITLAB_IMAGE = "gitlab/gitlab-ce"
            [envs.bench]
            detached = true
            ''',
            [
                ("py3.11-9", "3.11"),
                ("py3.11-10", "3.11"),
                ("py3.13-9", "3.13"),
                ("py3.13-10", "3.13"),
                ("py3.13-9-cluster", "3.13"),
            ],
            id="multiple-matrices",
        ),
    ],
)
def test_hatch_environments_expand_names_and_python_on_each_platform(
    tmp_path: Path, config: str, expected: list[tuple[str, str]]
):
    integration = integration_with_config(tmp_path, config)
    platforms = [PlatformName.LINUX, PlatformName.WINDOWS]

    environments = HatchEnvironmentProvider("3.13")(integration, platforms)

    assert [(e.name, e.python_version, e.platform) for e in environments] == [
        (name, python, platform) for name, python in expected for platform in platforms
    ]


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        pytest.param(
            '[envs.default]\nplatforms = ["windows"]',
            [("default", PlatformName.WINDOWS)],
            id="literal-platforms",
        ),
        pytest.param(
            '[[envs.default.matrix]]\npython = ["3.13"]\nos = ["linux", "windows"]',
            [("py3.13-linux", PlatformName.LINUX), ("py3.13-windows", PlatformName.WINDOWS)],
            id="os-convention",
        ),
        pytest.param(
            '''
            [[envs.default.matrix]]
            python = ["3.13"]
            os = ["linux", "windows"]
            [envs.default.overrides]
            matrix.os.platforms = [
              { value = "windows", if = ["windows"] },
              { value = "linux", if = ["linux"] },
              { value = "macos", if = ["linux"] },
            ]
            ''',
            [
                ("py3.13-linux", PlatformName.LINUX),
                ("py3.13-linux", PlatformName.MACOS),
                ("py3.13-windows", PlatformName.WINDOWS),
            ],
            id="sqlserver-platform-map",
        ),
    ],
)
def test_hatch_environments_route_platforms(tmp_path: Path, config: str, expected: list[tuple[str, PlatformName]]):
    integration = integration_with_config(tmp_path, config)

    environments = HatchEnvironmentProvider("3.13")(
        integration, [PlatformName.LINUX, PlatformName.MACOS, PlatformName.WINDOWS]
    )

    assert [(e.name, e.platform) for e in environments] == expected


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        pytest.param('[envs.default]', [(True, True)], id="standard-stages"),
        pytest.param('[envs.default]\ntest-env = true', [(True, True)], id="explicit-unit-tests"),
        pytest.param('[envs.default]\ne2e-env = false', [(True, False)], id="unit-only"),
        pytest.param(
            '''
            [envs.default]
            e2e-env = false
            [envs.default.overrides]
            env.IOT_EDGE_CONNSTR.e2e-env = { value = true }
            ''',
            [(True, True)],
            id="runtime-enablement",
        ),
        pytest.param(
            '''
            [envs.default.overrides]
            platform.windows.e2e-env = { value = false }
            ''',
            [(True, True)],
            id="runtime-disablement",
        ),
    ],
)
def test_hatch_environments_resolve_stages_and_defer_conditional_e2e(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: str, expected: list[tuple[bool, bool]]
):
    integration = integration_with_config(tmp_path, config)
    provider = HatchEnvironmentProvider("3.13")

    monkeypatch.delenv("IOT_EDGE_CONNSTR", raising=False)
    environments = provider(integration, [PlatformName.WINDOWS])

    assert [(e.test_available, e.e2e_available) for e in environments] == expected


@pytest.mark.parametrize(
    ("config", "field"),
    [
        pytest.param('[envs.default]\ntest-env = false', "envs.default.test-env", id="disabled-unit-tests"),
        pytest.param(
            '[envs.default.overrides]\nenv.RUN_UNIT.test-env = { value = true }',
            "envs.default.overrides.env.RUN_UNIT.test-env",
            id="unit-test-enablement-override",
        ),
        pytest.param(
            '[envs.default.overrides]\nplatform.windows.test-env = { value = false }',
            "envs.default.overrides.platform.windows.test-env",
            id="unit-test-disablement-override",
        ),
        pytest.param('[envs.default]\npython = "3.13t"', "envs.default.python", id="unsupported-python"),
        pytest.param('[envs.default]\nplatforms = "linux"', "envs.default.platforms", id="invalid-platform-list"),
        pytest.param('[[envs.default.matrix]]\npython = []', "envs.default.matrix[0].python", id="empty-axis"),
        pytest.param('[[envs.default.matrix]]\npython = [3.13]', "envs.default.matrix[0].python", id="numeric-axis"),
        pytest.param('[[envs.default.matrix]]\nversion = ["bad name"]', "invalid environment name", id="unsafe-name"),
        pytest.param(
            '[[envs.default.matrix]]\nversion = ["same", "same"]',
            "duplicate environment name",
            id="duplicate-name",
        ),
        pytest.param('[envs.default]\ntemplate = "other"', "envs.default.template", id="inheritance"),
        pytest.param(
            '[envs.default]\nmatrix-name-format = "{variable}-{value}"',
            "envs.default.matrix-name-format",
            id="custom-naming",
        ),
        pytest.param('[env.collectors.custom]\npath = "hatch_plugin.py"', "env.collectors", id="custom-collector"),
        pytest.param('[envs.extra]\ntest-env = true', "envs.extra", id="named-test-environment"),
        pytest.param(
            '''
            [env.collectors.default]
            [envs.default]
            python = "3.13"
            test-env = true
            e2e-env = false
            [envs.extra]
            template = "default"
            ''',
            "envs.extra.template",
            id="named-inheritance",
        ),
        pytest.param(
            '[envs.default.overrides]\nenv.PYTHON.python = { value = "3.11" }',
            "envs.default.overrides.env.PYTHON.python",
            id="dynamic-python",
        ),
        pytest.param(
            '[envs.default.overrides]\nname.special.platforms = ["windows"]',
            "envs.default.overrides.name.special.platforms",
            id="dynamic-platforms",
        ),
        pytest.param('[envs.default', "sample/hatch.toml", id="invalid-toml"),
    ],
)
def test_hatch_environments_report_unreliable_discovery(tmp_path: Path, config: str, field: str):
    integration = integration_with_config(tmp_path, config)

    with pytest.raises(PlanningError, match=re.escape(field)) as error:
        HatchEnvironmentProvider("3.13")(integration, [PlatformName.LINUX])

    assert "sample/hatch.toml" in str(error.value)
