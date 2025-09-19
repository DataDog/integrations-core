import pytest

from ddev.utils.fs import Path
from ddev.utils.metadata import (
    InvalidMetadataError,
    PyProjectNotFoundError,
    RepoNotFoundError,
    ValidRepo,
    pyproject_metadata,
)
from ddev.utils.toml import dump_toml_data, load_toml_file
from tests.helpers.git import ClonedRepo


def test_pyproject_metadata_not_in_repo(temp_dir: Path):
    with temp_dir.as_cwd():
        with pytest.raises(RepoNotFoundError):
            pyproject_metadata()


def test_pyproject_metadata_wihtout_pyproject_file(repository: ClonedRepo):
    with repository.path.as_cwd():
        (repository.path / "pyproject.toml").unlink()

        with pytest.raises(PyProjectNotFoundError):
            pyproject_metadata()


def test_pyproject_metadata_without_tool_config(repository: ClonedRepo):
    with repository.path.as_cwd():
        data = load_toml_file("pyproject.toml")
        # Remove the tool.ddev table if it exists
        if "tool" in data and "ddev" in data["tool"]:
            data["tool"].pop("ddev")
            dump_toml_data(data, "pyproject.toml")

        assert pyproject_metadata() is None


@pytest.mark.parametrize("repo", ValidRepo, ids=lambda r: r.value)
def test_pyproject_metadata_with_tool_config(repository_as_cwd: ClonedRepo, repo: ValidRepo):
    data = load_toml_file("pyproject.toml")
    data["tool"]["ddev"] = {"repo": repo.value}
    dump_toml_data(data, "pyproject.toml")
    metadata = pyproject_metadata()
    assert metadata is not None
    assert metadata.repo == repo


def test_pyproject_metadata_with_tool_config_invalid_repo(repository_as_cwd: ClonedRepo):
    data = load_toml_file("pyproject.toml")
    data["tool"]["ddev"] = {"repo": "invalid-repo"}
    dump_toml_data(data, "pyproject.toml")

    with pytest.raises(InvalidMetadataError) as e:
        pyproject_metadata()

    message = e.value.message
    expected_values = [f"{r.value!r}" for r in ValidRepo]
    expected_values = ", ".join(expected_values[:-1]) + " or " + expected_values[-1]
    expected_body = [
        "Invalid ddev metadata found in pyproject.toml:",
        (f"  - [tool.ddev.repo] is 'invalid-repo': Input should be {expected_values}"),
    ]
    assert message == "\n".join(expected_body)


def test_pyproject_metadata_with_missing_repo_key(repository_as_cwd: ClonedRepo):
    data = load_toml_file("pyproject.toml")
    data["tool"]["ddev"] = {}
    dump_toml_data(data, "pyproject.toml")

    with pytest.raises(InvalidMetadataError) as e:
        pyproject_metadata()

    message = e.value.message
    expected_body = [
        "Invalid ddev metadata found in pyproject.toml:",
        "  - [tool.ddev]: The 'repo' field is required",
    ]
    assert message == "\n".join(expected_body)
