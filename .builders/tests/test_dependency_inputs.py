import pytest

from dependency_inputs import affects_resolution, is_resolution_output


@pytest.mark.parametrize(
    'path',
    [
        'agent_requirements.in',
        '.github/workflows/resolve-build-deps.yaml',
        '.builders/build.py',
        '.builders/images/linux-x86_64/Dockerfile',
        '.builders/scripts/build_wheels.py',
    ],
)
def test_resolution_inputs_are_classified(path):
    assert affects_resolution(path)


@pytest.mark.parametrize(
    'path',
    [
        '.builders/promote.py',
        '.builders/dependency_wheel_promotion_gate.py',
        '.builders/tests/test_promote.py',
        '.builders/scripts/.hidden',
        '.builders/images/__pycache__/cached.pyc',
        'README.md',
    ],
)
def test_non_inputs_are_ignored(path):
    assert not affects_resolution(path)


def test_only_visible_deps_files_are_resolution_output():
    assert is_resolution_output('.deps/resolved/linux-x86_64_3.13.txt')
    assert not is_resolution_output('.deps/.hidden')
    assert not is_resolution_output('.deps/resolved/__pycache__/cached')
