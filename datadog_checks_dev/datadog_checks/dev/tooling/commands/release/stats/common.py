# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import re

from ....github import (
    get_commit,
    get_compare,
    get_pr_from_hash,
    get_pr_labels,
    get_pr_of_repo,
    get_tag,
    get_tags,
    parse_pr_number,
)
from ...console import echo_failure, echo_info


class PullRequest:
    def __init__(self, repo, number, title, url, labels):
        self.repo = repo
        self.number = number
        self.title = title
        self.url = url
        self.labels = labels

    @classmethod
    def from_github(cls, ctx, repo, number):
        gh_pr = get_pr_of_repo(number, repo, config=ctx.obj)
        return PullRequest(
            repo=repo, number=gh_pr['number'], title=gh_pr['title'], url=gh_pr['html_url'], labels=get_pr_labels(gh_pr)
        )

    @classmethod
    def from_commit(cls, ctx, repo, commit_message, commit_sha):
        pr_number = parse_pr_number(commit_message)

        if pr_number is None:
            echo_info(f"Could not parse PR number from commit '{commit_sha}' - Will look for an issue with it...")
            found_items = get_pr_from_hash(commit_sha, repo, config=ctx.obj)['items']

            if len(found_items) == 0:
                echo_failure(f"Could not find relevant PR of commit '{commit_sha}'")
                return None

            pr_number = found_items[0]['number']
            echo_info(f"Found issue '{pr_number}'")

        return PullRequest.from_github(ctx, repo, pr_number)


class Commit:
    def __init__(self, repo, sha, title, date, author, pull_request, included_in_tag=None):
        self.repo = repo
        self.sha = sha
        self.title = title
        self.date = date
        self.author = author
        self.pull_request = pull_request
        self.url = f'https://www.github.com/DataDog/{repo}/commit/{sha}'
        self.included_in_tag = included_in_tag

    def included_in(self, next_tag):
        self.included_in_tag = next_tag

    @classmethod
    def from_github_commit(cls, ctx, repo, gh_commit):
        pull_request = PullRequest.from_commit(ctx, repo, gh_commit['commit']['message'], gh_commit['sha'])

        return Commit(
            repo=repo,
            sha=gh_commit['sha'],
            title=gh_commit['commit']['message'],
            date=datetime.datetime.strptime(gh_commit['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ'),
            author=f"@{gh_commit['committer']['login']} - {gh_commit['commit']['committer']['name']}",
            pull_request=pull_request,
        )

    @classmethod
    def from_github_compare(cls, ctx, repo, from_ref, to_ref):
        comparison = get_compare(from_ref, to_ref, repo, config=ctx.obj)

        return [Commit.from_github_commit(ctx, repo, gh_commit) for gh_commit in comparison['commits']]

    @classmethod
    def get(cls, ctx, repo, sha):
        gh_commit = get_commit(repo, sha, config=ctx.obj)

        return Commit.from_github_commit(ctx, repo, gh_commit)


class Tag:
    def __init__(self, repo, ref, sha, commit_sha=None):
        self.repo = repo
        self.ref = ref
        self.name = ref.rpartition('/')[-1]
        self.sha = sha
        self.commit_sha = commit_sha

    def reload(self, ctx):
        tag = Tag.get(ctx, self.repo, self.sha)

        self.repo = tag.repo
        self.ref = tag.ref
        self.name = tag.name
        self.sha = tag.sha
        self.commit_sha = tag.commit_sha

        return self

    @classmethod
    def from_github_tag(cls, repo, gh_tag):
        if gh_tag['object']['type'] == 'commit':
            return Tag(
                repo=repo,
                ref=gh_tag.get('ref', gh_tag.get('tag')),
                sha=gh_tag.get('sha', None),
                commit_sha=gh_tag['object']['sha'],
            )
        else:
            return Tag(repo=repo, ref=gh_tag['ref'], sha=gh_tag['object']['sha'])

    @classmethod
    def get(cls, ctx, repo, tag_sha):
        return Tag.from_github_tag(repo, get_tag(repo, tag_sha, config=ctx.obj))

    @classmethod
    def list_from_github(cls, ctx, repo):
        gh_tags = get_tags(repo, config=ctx.obj)
        return [Tag.from_github_tag(repo, gh_tag) for gh_tag in gh_tags]


class Release:
    def __init__(self, repo, release_version, commits, rc_tags):
        self.repo = repo
        self.release_version = release_version
        self.commits = commits
        self.rc_tags = rc_tags

    def release_duration_days(self):
        # Returns the number of days between the first and last change
        rc_1 = self.commits[0]
        last_change = self.commits[-1]
        duration = (last_change.date - rc_1.date).total_seconds()
        return divmod(duration, 24 * 60 * 60)[0]

    @classmethod
    def from_github(cls, ctx, repo, release_version, from_ref, to_ref):
        # this will only contain agent 7 or 6 RCs but it's okay
        # as we want versions to assign commits / count them
        version_re = re.compile(f'{release_version}-rc')
        # comparing using provided references but using parent commit of from-reference to
        # also have the from-ref commit included
        echo_info(f'Fetching commits from "{repo}" using compare from parent of "{from_ref}" to "{to_ref}"...')
        commits = Commit.from_github_compare(ctx, repo, f'{from_ref}^', to_ref)
        echo_info(f'Fetching tags matching "/{version_re}/"...')
        rc_tags = [
            tag for tag in Tag.list_from_github(ctx, repo) if version_re.match(tag.name) or tag.name == release_version
        ]

        # Exclude any tags with "-dbm-beta-" in the name. DB APM recently have used
        # similar tags (e.g. `7.28.0-rc.1-dbm-beta-0.1`) for beta builds for clients
        # and for deploying to classic that need to be filtered out, otherwise the
        # dependent scripts get confused about what constitutes an "rc" tag.
        rc_tags = [tag for tag in rc_tags if '-dbm-beta-' not in tag.name]

        for rc_tag in rc_tags:
            # we are forced to reload tags as the github does not return the tag's commit's SHA
            # when we are using the tag list API
            if rc_tag.commit_sha is None:
                echo_info(f'Reloading tag "{rc_tag.name}" as it does not have a commit SHA')
                rc_tag.reload(ctx)

        echo_info('Assigning release candidates to commits...')
        # assign commits to release candidates
        tag_index = 0

        for commit in commits:
            # break if we cannot assign tags to commits anymore
            if tag_index >= len(rc_tags):
                echo_failure("Could not assign a tag to every commits")
                break

            commit.included_in(rc_tags[tag_index])

            if commit.sha == rc_tags[tag_index].commit_sha:
                tag_index += 1

        return Release(repo=repo, release_version=release_version, commits=commits, rc_tags=rc_tags)
