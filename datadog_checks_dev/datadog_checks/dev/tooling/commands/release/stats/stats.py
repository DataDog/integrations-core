# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
from pathlib import Path

import click

from ...console import CONTEXT_SETTINGS, echo_success
from .common import Release


class ReportSerializer:
    def __init__(self, release):
        self.release = release

    def print_prs(self):
        changes = [self._change(commit) for commit in self.release.commits]
        for change in changes:
            print(','.join([change[field] for field in ['url', 'teams', 'next_tag', 'title']]))

    def print_report(self):
        print('Release Branch', self.release.release_version)
        print('Release candidates', len(self.release.rc_tags))
        print('Number of Commits', len(self.release.commits))
        print('Commits with unknown PR', len([commit for commit in self.release.commits if commit.pull_request is None]))
        print('Release time (days)', self._release_delay())

    def _release_delay(self):
        rc_1 = self.release.commits[0]
        last_change = self.release.commits[-1]

        duration = (last_change.date - rc_1.date).total_seconds()

        return divmod(duration, 24 * 60 * 60)[0]

    def _change(self, commit):
        teams = []
        title = commit.title
        url = commit.url
        next_tag = None

        pull_request = commit.pull_request

        if pull_request:
            teams = [label.rpartition('/')[-1] for label in pull_request.labels if label.startswith('team')]
            title = pull_request.title
            url = pull_request.url

        if commit.included_in_tag:
            next_tag = commit.included_in_tag.name

        return {'sha': commit.sha, 'title': title, 'url': url, 'teams': ' & '.join(teams), 'next_tag': next_tag}


@click.command(context_settings=CONTEXT_SETTINGS, short_help="Prints the PRs merged between the first RC and the current RC/final build")
@click.option('--from-ref', '-f', help="Reference to start stats on (first RC tagged)", required=True)
@click.option('--to-ref', '-t', help="Reference to end stats at (current RC/final tag)", required=True)
@click.option('--release-milestone', '-r', help="Github release milestone", required=True)
@click.pass_context
def merged_prs(ctx, from_ref, to_ref, release_milestone):

    release = Release.from_github(ctx, release_milestone, from_ref=from_ref, to_ref=to_ref)

    serializer = ReportSerializer(release)
    serializer.print_prs()


@click.command(context_settings=CONTEXT_SETTINGS, short_help="Prints some release stats we want to track")
@click.option('--from-ref', '-f', help="Reference to start stats on (first RC tagged)", required=True)
@click.option('--to-ref', '-t', help="Reference to end stats at (current RC/final tag)", required=True)
@click.option('--release-milestone', '-r', help="Github release milestone", required=True)
@click.pass_context
def report(ctx, from_ref, to_ref, release_milestone):

    release = Release.from_github(ctx, release_milestone, from_ref=from_ref, to_ref=to_ref)

    serializer = ReportSerializer(release)
    serializer.print_report()
