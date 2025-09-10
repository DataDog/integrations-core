import click
from datadog_checks.dev.tooling.codeowners import CodeOwners

from ddev.cli.application import Application


@click.command()
@click.option('--pr', help='Check the codeowners for the given PR')
@click.option('--sha', help='Check the codeowners for the given sha')
@click.option('--files', help='Check the codeowners for the given files separated by commas')
@click.option('--per-file', is_flag=True, help='Output the codeowners for each file')
@click.pass_obj
def codeowners(app: Application, pr: str, sha: str, files: str, per_file: bool):
    """
    Check the codeowners for the given PR, commit, or files.
    """
    codeowners_file = app.repo.path / '.github' / 'CODEOWNERS'
    with open(codeowners_file, 'r') as f:
        codeowners_content = f.readlines()
    codeowners: CodeOwners = CodeOwners("\n".join(codeowners_content))

    if files:
        file_list = files.split(',') if ',' in files else [files]
    elif pr:
        github = app.github
        pr_obj = github.get_pull_request_by_number(pr)
        if pr_obj is None:
            app.display_error(f'Pull request {pr} not found')
            return
        file_list = github.get_changed_files_by_pr(pr_obj)
    elif sha:
        github = app.github
        files_by_sha = github.get_changed_files_by_sha(sha)
        if files_by_sha is None:
            app.display_error(f'Commit {sha} not found')
            return
        file_list = files_by_sha
    else:
        app.display_error('No files provided')
        return
    if per_file:
        owners_per_file = map_files_to_teams(file_list, codeowners)
        app.display_info(owners_per_file)
    else:
        owners = get_owners(file_list, codeowners)
        app.display_info(sorted(owners))


def map_files_to_teams(files: list[str], codeowners: CodeOwners) -> dict[str, list[str]]:
    file_to_owners = {}
    for file in files:
        file = file.strip()
        if file:
            owners = codeowners.of(file)
            if owners:
                # Collect all owner names for this file in a list
                owner_names = [owner_name for _, owner_name in owners]
                file_to_owners[file] = sorted(owner_names)
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
