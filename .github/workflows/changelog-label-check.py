from github import Github
import re


repo = Github().get_repo(get_env_var('GITHUB_REPOSITORY'))
pr_number = int(re.search('refs/pull/([0-9]+)/merge', get_env_var('GITHUB_REF')).group(1))
pr_labels = repo.get_pull(pr_number).get_labels()

changelog_labels = list(filter(lambda label: label.name.startswith('changelog'), pr_labels))

if len(changelog_labels) == 0:
    raise Exception('There is no changelog label.')
if len(changelog_labels) > 1:
    raise Exception('There is more than on changelog label.')
