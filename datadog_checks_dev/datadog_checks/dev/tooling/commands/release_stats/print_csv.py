# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import re
import datetime
import csv

from collections import namedtuple
from pathlib import Path

from ....utils import write_file_lines
from ..console import CONTEXT_SETTINGS, echo_failure, echo_info, echo_success
from ...github import get_compare, parse_pr_number, get_pr_from_hash, get_tags, get_tag, get_pr_of_repo, get_pr_labels, get_commit

class PullRequest:
    def __init__(self, number, title, url, labels):
        self.number = number
        self.title = title
        self.url = url
        self.labels = labels

    @classmethod
    def from_github_pr(cls, gh_pr):
        return PullRequest(
            number=gh_pr['number'],
            title=gh_pr['title'],
            url=gh_pr['html_url'],
            labels=get_pr_labels(gh_pr)
        )

    @classmethod
    def from_github(cls, ctx, number):
        gh_pr = get_pr_of_repo(number, 'datadog-agent', config=ctx.obj)

        return PullRequest.from_github_pr(gh_pr)

    @classmethod
    def from_commit(cls, ctx, commit_message, commit_sha):
        pr_number = parse_pr_number(commit_message)

        if pr_number is None:
            echo_info(f"Could not parse PR number from commit '{commit_sha}' - Will look for an issue with it...")
            found_items = get_pr_from_hash(commit_sha, 'datadog-agent', config=ctx.obj)['items']

            if len(found_items) == 0:
                echo_failure(f"Could not find relevant PR of commit '{commit_sha}'")
                return None

            pr_number = found_items[0]['number']
            echo_info(f"Found issue '{pr_number}'")

        return PullRequest.from_github(ctx, pr_number)

class Commit:
    def __init__(self, sha, title, date, author, pull_request, parent_shas=[]):
        self.sha = sha
        self.title = title
        self.date = date
        self.author = author
        self.pull_request = pull_request
        self.parent_shas = parent_shas
        self.url = f'https://www.github.com/DataDog/datadog-agent/commit/{sha}'

    def to_change(self):
        teams = []
        title = self.title
        url = self.url

        if self.pull_request:
            teams = [ label.rpartition('/')[-1] for label in self.pull_request.labels if label.startswith('team') ]
            title = self.pull_request.title
            url = self.pull_request.url

        return {
            'SHA': self.sha,
            'Title': title,
            'URL': url,
            'Teams': ' & '.join(teams)
        }

    @classmethod
    def from_github_commit(cls, ctx, gh_commit):
        pull_request = PullRequest.from_commit(ctx, gh_commit['commit']['message'], gh_commit['sha'])

        return Commit(
            sha=gh_commit['sha'],
            title=gh_commit['commit']['message'],
            date=datetime.datetime.strptime(gh_commit['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ'),
            author=f"@{gh_commit['committer']['login']} - {gh_commit['commit']['committer']['name']}",
            pull_request=pull_request,
            parent_shas=[ parent['sha'] for parent in gh_commit['parents'] ]
        )

    @classmethod
    def from_github_branch_head(cls, ctx, branch, from_ref='master'):
        comparison = get_compare(from_ref, branch, 'datadog-agent', config=ctx.obj)

        return [ Commit.from_github_commit(ctx, gh_commit) for gh_commit in comparison['commits'] ]

    @classmethod
    def get(cls, ctx, sha):
        gh_commit = get_commit('datadog-agent', sha, config=ctx.obj)

        return Commit.from_github_commit(ctx, gh_commit)


class Tag:
    def __init__(self, ref, sha, commit_sha=None):
        self.ref = ref
        self.name = ref.rpartition('/')[-1]
        self.sha = sha
        self.commit_sha = commit_sha

    def reload(self, ctx):
        tag = Tag.get(ctx, self.sha)

        self.ref = tag.ref
        self.name = tag.name
        self.sha = tag.sha
        self.commit_sha = tag.commit_sha

    @classmethod
    def from_github_tag(cls, gh_tag):
        if gh_tag['object']['type'] == 'commit':
            return Tag(
                ref=gh_tag['ref'],
                sha=gh_tag.get('sha', None),
                commit_sha=gh_tag['object']['sha']
            )
        else:
            return Tag(
                ref=gh_tag['ref'],
                sha=gh_tag['object']['sha']
            )

    @classmethod
    def get(cls, ctx, tag_sha):
        Tag.from_github_tag(get_tag('datadog-agent', tag_sha, config=ctx.obj))

    @classmethod
    def list_from_github(cls, ctx):
        gh_tags = get_tags('datadog-agent', config=ctx.obj)
        return [ Tag.from_github_tag(gh_tag) for gh_tag in gh_tags ]

class Release:
    def __init__(self, release_branch, commits, rc_tags):
        self.release_branch = release_branch
        self.commits = commits
        self.rc_tags = rc_tags

    def to_report(self):
        return {
            'Release Branch': self.release_branch,
            'Release candidates': len(self.rc_tags),
            'Number of Commits': len(self.commits),
            'Commits with unknown PR': len([commit for commit in self.commits if commit.pull_request is None ]),
            'Release time (days)': self._release_delay()
        }

    def write_report(self, filepath):
        with open(filepath, 'w', newline='') as csvfile:
            report = self.to_report()

            fieldnames = report.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerow(report)

    def write_changes(self, filepath):
        changes = [ commit.to_change() for commit in self.commits ]

        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = changes[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for change in changes:
                writer.writerow(change)

    def _release_delay(self):
        rc_1 = self.commits[0]
        last_change = self.commits[-1]

        duration = (last_change.date - rc_1.date).total_seconds()

        return divmod(duration, 24 * 60 * 60)[0]

    @classmethod
    def from_github(cls, ctx, release_branch, from_ref=None):
        base_version = release_branch.rpartition('.')[0]
        branch_re = re.compile(f'{base_version}\.\d+-rc') # this will only contain agent 7 RCs but it's okay
        rc_tags = [ tag for tag in Tag.list_from_github(ctx) if branch_re.match(tag.name) ]

        # choose base ref to compare to the release branch to get commits made after freeze
        base_ref = None

        if from_ref:
            echo_info(f"Using provided ref '{from_ref}' as base commit")
            base_ref = from_ref
        else:
            # try to find rc1 tag to use as base commit
            rc1_tag_name = f"{base_version}.0-rc.1"
            rc1_tag = None

            for rc_tag in rc_tags:
                if rc_tag.name == rc1_tag_name:
                    rc1_tag = rc_tag
                    break

            if rc1_tag:
                echo_info(f"Using parent commit of tag '{rc1_tag.name}' as base commit")
                base_ref = f'{rc1_tag_name}^'
            else:
                raise ArgumentError('Did not any rc.1 tag to use as base commit')

        return Release(
            release_branch=release_branch,
            commits=Commit.from_github_branch_head(ctx, release_branch, from_ref=base_ref),
            rc_tags=rc_tags
        )


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Writes the CSV report about a specific release",
)
@click.option('--branch', '-b', help="Release branch to make stats on", required=True)
@click.option('--base-commit', '-c', help="First 8 characters of the commit sha to use as base")
@click.option('--output-folder', '-o', help="Path to output folder")
@click.pass_context
def print_csv(ctx, branch, base_commit=None, output_folder=None):
    """Computes the release report and writes it to a specific directory
    """
    if output_folder is None:
        output_folder = branch

    # print(get_tag('datadog-agent', '94f74d70abb0512bd0ed0fae9e50206d3b087cdb', config=ctx.obj))

    folder = Path(output_folder)

    folder.mkdir(parents=True, exist_ok=True)

    release = Release.from_github(ctx, branch, from_ref=base_commit)

    release.write_report(folder.joinpath('release.csv'))
    release.write_changes(folder.joinpath('changes.csv'))

    echo_success(f'Successfully wrote reports to directory `{output_folder}`')


