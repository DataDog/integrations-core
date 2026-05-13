import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from process_analyze import (
    Process,
    CollectedData,
    SkipEntry,
    ServiceVerdict,
    IntegrationResult,
    find_integrations_with_e2e,
    parse_ddev_env_show,
    select_environment,
)


SAMPLE_DDEV_ENV_SHOW = """\
Available
┏━━━━━━━━━━━━━┓
┃ Name        ┃
┡━━━━━━━━━━━━━┩
│ py3.13-1.12 │
├─────────────┤
│ py3.13-1.13 │
├─────────────┤
│ py3.13-1.27 │
├─────────────┤
│ py3.13-vts  │
└─────────────┘
"""


def test_imports():
    p = Process(pid=1, ppid=0, comm="nginx", cmdline="nginx", generated_name="nginx", has_service_data=True)
    assert p.pid == 1


def test_parse_ddev_env_show():
    envs = parse_ddev_env_show(SAMPLE_DDEV_ENV_SHOW)
    assert envs == ["py3.13-1.12", "py3.13-1.13", "py3.13-1.27", "py3.13-vts"]


def test_select_environment_prefers_version():
    envs = ["py3.13-1.12", "py3.13-1.13", "py3.13-1.27", "py3.13-vts"]
    assert select_environment(envs) == "py3.13-1.27"


def test_select_environment_falls_back_to_last():
    envs = ["py3.13-vts", "py3.13-plus"]
    assert select_environment(envs) == "py3.13-plus"


def test_select_environment_empty():
    assert select_environment([]) is None


def test_find_integrations_with_e2e(tmp_path):
    # Create fake integration directories
    for name in ["nginx", "redis", "no_e2e"]:
        tests = tmp_path / name / "tests"
        tests.mkdir(parents=True)
        if name != "no_e2e":
            (tests / "test_e2e.py").touch()

    result = find_integrations_with_e2e(tmp_path)
    assert result == ["nginx", "redis"]
