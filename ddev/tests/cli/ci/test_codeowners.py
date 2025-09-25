from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Sample CODEOWNERS content for testing
CODEOWNERS_CONTENT = """

# Folder 1
/.folder1/                        @DataDog/team1 @DataDog/team2
/.folder2/                        @DataDog/team2

# Folder 2
/folder3/                     @DataDog/team1 @DataDog/team2
/folder3/*.md                 @DataDog/team1 @DataDog/team2 @DataDog/team3
"""


@pytest.fixture
def temp_repo(tmp_path: Path, monkeypatch) -> Path:
    repo_path = tmp_path

    github_dir = repo_path / ".github"
    github_dir.mkdir()
    codeowners_file = github_dir / "CODEOWNERS"
    codeowners_file.write_text(CODEOWNERS_CONTENT)

    # Ensure CLI operates in this temporary repo
    monkeypatch.chdir(repo_path)
    return repo_path


@pytest.fixture
def mock_github():
    changed_files = ["/.folder1/mock.txt", "/folder3/mock.md"]
    with (
        patch('ddev.utils.github.GitHubManager.get_pull_request_by_number', return_value=MagicMock()),
        patch('ddev.utils.github.GitHubManager.get_changed_files_by_pr', return_value=changed_files),
        patch('ddev.utils.github.GitHubManager.get_changed_files_by_commit_sha', return_value=changed_files),
    ):
        yield


def test_codeowners_files(ddev, temp_repo):
    files_to_check = "/.folder1/mock.txt,/folder3/mock.md"

    result = ddev('--here', 'ci', 'codeowners', '--files', files_to_check)
    print(result.output)
    assert result.exit_code == 0
    expected_output = "['@DataDog/team1', '@DataDog/team2', '@DataDog/team3']\n"
    assert result.output == expected_output


def test_codeowners_file_per_file(ddev, temp_repo):
    files_to_check = "/.folder1/mock.txt,/folder3/mock.md"

    result = ddev('--here', 'ci', 'codeowners', '--files', files_to_check, '--per-file')
    assert result.exit_code == 0
    expected_output = (
        "{\n"
        "    '/.folder1/mock.txt': ['@DataDog/team1', '@DataDog/team2'],\n"
        "    '/folder3/mock.md': ['@DataDog/team1', '@DataDog/team2', '@DataDog/team3']\n"
        "}\n"
    )
    assert result.output == expected_output


def test_codeowners_pr(ddev, temp_repo, mock_github):
    result = ddev('--here', 'ci', 'codeowners', '--pr', '1')
    assert result.exit_code == 0
    expected_output = "['@DataDog/team1', '@DataDog/team2', '@DataDog/team3']\n"
    assert result.output == expected_output


def test_codeowners_pr_per_file(ddev, temp_repo, mock_github):
    result = ddev('--here', 'ci', 'codeowners', '--pr', '1', '--per-file')
    assert result.exit_code == 0
    expected_output = (
        "{\n"
        "    '/.folder1/mock.txt': ['@DataDog/team1', '@DataDog/team2'],\n"
        "    '/folder3/mock.md': ['@DataDog/team1', '@DataDog/team2', '@DataDog/team3']\n"
        "}\n"
    )
    assert result.output == expected_output


def test_codeowners_sha(ddev, temp_repo, mock_github):
    result = ddev('--here', 'ci', 'codeowners', '--commit-sha', '1234567890')
    assert result.exit_code == 0
    expected_output = "['@DataDog/team1', '@DataDog/team2', '@DataDog/team3']\n"
    assert result.output == expected_output


def test_codeowners_sha_per_file(ddev, temp_repo, mock_github):
    result = ddev('--here', 'ci', 'codeowners', '--commit-sha', '1234567890', '--per-file')
    assert result.exit_code == 0
    expected_output = (
        "{\n"
        "    '/.folder1/mock.txt': ['@DataDog/team1', '@DataDog/team2'],\n"
        "    '/folder3/mock.md': ['@DataDog/team1', '@DataDog/team2', '@DataDog/team3']\n"
        "}\n"
    )
    assert result.output == expected_output
