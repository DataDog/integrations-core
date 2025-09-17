import click
from datadog_checks.dev.tooling.codeowners import CodeOwners

from ddev.cli.application import Application


@click.command()
@click.option('--pr', help='Check the codeowners for the given PR')
@click.option('--commit-sha', help='Check the codeowners for the given commit SHA')
@click.option('--files', help='Check the codeowners for the given files separated by commas')
@click.option('--per-file', is_flag=True, help='Output the codeowners for each file')
@click.pass_obj
def codeowners(app: Application, pr: str, commit_sha: str, files: str, per_file: bool):
    """
    Check the codeowners for the given PR, commit, or files.
    """
    # Check that only one of pr, commit_sha, or files is provided
    selected_options = [opt for opt in (pr, commit_sha, files) if opt]
    if len(selected_options) != 1:
        app.display_error('Please provide exactly one of --pr, --commit-sha, or --files')
        return

    codeowners_file = app.repo.path / '.github' / 'CODEOWNERS'
    if not codeowners_file.exists():
        raise FileNotFoundError(f"{codeowners_file} does not exist")

    codeowners_content = codeowners_file.read_text()
    codeowners = CodeOwners(codeowners_content)

    if files:
        file_list = files.split(',') if ',' in files else [files]
    elif pr:
        github = app.github
        pr_obj = github.get_pull_request_by_number(pr)
        if pr_obj is None:
            app.display_error(f'Pull request {pr} not found')
            return
        file_list = github.get_changed_files_by_pr(pr_obj)
    elif commit_sha:
        github = app.github
        files_by_commit_sha = github.get_changed_files_by_commit_sha(commit_sha)
        if files_by_commit_sha is None:
            app.display_error(f'Commit {commit_sha} not found')
            return
        file_list = files_by_commit_sha

    if per_file:
        owners_per_file = get_owners_per_file(file_list, codeowners)
        app.display_info(owners_per_file)
    else:
        owners = get_owners(file_list, codeowners)
        app.display_info(sorted(owners))


def get_owners_per_file(files: list[str], codeowners: CodeOwners) -> dict[str, list[str]]:
    file_to_owners = {}
    for file in files:
        file = file.strip()
        if file:
            owners = codeowners.of(file)
            if owners:
                # Collect all owner names for this file in a list
                owner_names = [owner_name for _, owner_name in owners]
                file_to_owners[file] = sorted(owner_names)
            else:
                file_to_owners[file] = ["No owners found"]

    return file_to_owners


def get_owners(files: list[str], codeowners: CodeOwners) -> set[str]:
    owners = set()
    for file in files:
        file = file.strip()
        if file:
            file_owners = codeowners.of(file)
            if file_owners:
                owners.update([owner_name for _, owner_name in file_owners])
    return owners
