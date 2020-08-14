from github import Github
import os
import re


repo = Github().get_repo(os.environ.get('GITHUB_REPOSITORY'))
pr_number = int(re.search('refs/pull/([0-9]+)/merge', os.environ.get('GITHUB_REF')).group(1))
pr_labels = repo.get_pull(pr_number).get_labels()

changelog_labels = list(filter(lambda label: label.name.startswith('changelog'), pr_labels))

if len(changelog_labels) == 0:
    raise Exception('There is no changelog label.')
if len(changelog_labels) > 1:
    raise Exception('There is more than on changelog label.')
