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

    def write_report(self, filepath):
        with open(filepath, 'w', newline='') as csvfile:
            report = self._report()

            fieldnames = report.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerow(report)

    def write_changes(self, filepath):
        with open(filepath, 'w', newline='') as csvfile:
            changes = [self._change(commit) for commit in self.release.commits]
            fieldnames = changes[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for change in changes:
                writer.writerow(change)

    def _report(self):
        return {
            'Release Branch': self.release.release_version,
            'Release candidates': len(self.release.rc_tags),
            'Number of Commits': len(self.release.commits),
            'Commits with unknown PR': len([commit for commit in self.release.commits if commit.pull_request is None]),
            'Release time (days)': self._release_delay(),
        }

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

        return {'SHA': commit.sha, 'Title': title, 'URL': url, 'Teams': ' & '.join(teams), 'Next tag': next_tag}


@click.command(context_settings=CONTEXT_SETTINGS, short_help="Writes the CSV report about a specific release")
@click.option('--from-ref', '-f', help="Reference to start stats on", required=True)
@click.option('--to-ref', '-t', help="Reference to end stats at", required=True)
@click.option('--release-version', '-r', help="Release version to analyze", required=True)
@click.option('--output-folder', '-o', help="Path to output folder")
@click.pass_context
def csv_report(ctx, from_ref, to_ref, release_version, output_folder=None):
    """Computes the release report and writes it to a specific directory"""
    if output_folder is None:
        output_folder = release_version

    folder = Path(output_folder)

    folder.mkdir(parents=True, exist_ok=True)

    release = Release.from_github(ctx, release_version, from_ref=from_ref, to_ref=to_ref)

    serializer = ReportSerializer(release)

    serializer.write_report(folder.joinpath('release.csv'))
    serializer.write_changes(folder.joinpath('changes.csv'))

    echo_success(f'Successfully wrote reports to directory `{output_folder}`')
