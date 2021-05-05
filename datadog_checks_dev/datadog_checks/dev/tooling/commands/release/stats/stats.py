# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv

import click

from ...console import CONTEXT_SETTINGS, echo_info
from .common import Release


def parse_commit(commit):
    teams = []
    title = commit.title
    url = commit.url
    next_tag = None

    pull_request = commit.pull_request

    if pull_request:
        teams = [label.rpartition('/')[-1] for label in pull_request.labels if label.startswith('team')]
        if not teams and pull_request.repo == 'integrations-core':
            teams = ['agent-integrations']
        title = pull_request.title
        url = pull_request.url

    if commit.included_in_tag:
        next_tag = commit.included_in_tag.name

    return {'sha': commit.sha, 'title': title, 'url': url, 'teams': ' & '.join(teams), 'next_tag': next_tag}


def export_changes_as_csv(changes, filename):
    with open(filename, "w") as release_csv:
        echo_info("Exporting csv as {}".format(filename))
        writer = csv.writer(release_csv)

        # Header
        writer.writerow(
            [
                'PR',
                'Team',
                'What RC was it included in?',
                'Short description',
                'Severity',
                'Was this a bug or something else?',
                'What could we have done differently or what could we do differently to find this bug earlier',
            ]
        )
        for change in changes:
            writer.writerow(
                [
                    change['url'],
                    change['teams'],
                    change['next_tag'].split('-')[-1] if '-' in change['next_tag'] else change['next_tag'],
                    change['title'],
                    '',
                    '',
                    '',
                ]
            )


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Prints the PRs merged between the first RC and the current RC/final build",
)
@click.option('--from-ref', '-f', help="Reference to start stats on (first RC tagged)", required=True)
@click.option('--to-ref', '-t', help="Reference to end stats at (current RC/final tag)", required=True)
@click.option('--release-milestone', '-r', help="Github release milestone", required=True)
@click.option(
    '--exclude-releases', '-e', help="Flag to exclude the release PRs from the list", required=False, is_flag=True
)
@click.option('--export-csv', help="CSV file where the list will be exported", required=False)
@click.pass_context
def merged_prs(ctx, from_ref, to_ref, release_milestone, exclude_releases, export_csv):
    agent_release = Release.from_github(ctx, 'datadog-agent', release_milestone, from_ref=from_ref, to_ref=to_ref)
    integrations_release = Release.from_github(
        ctx, 'integrations-core', release_milestone, from_ref=from_ref, to_ref=to_ref
    )

    changes = [parse_commit(commit) for commit in agent_release.commits + integrations_release.commits]

    if exclude_releases:
        filtered_changes = []
        for change in changes:
            title = change['title'].lower()
            if not title.startswith('[release]') and not title.startswith('release'):
                filtered_changes.append(change)
        changes = filtered_changes

    changes = sorted(changes, key=lambda x: x['next_tag'])  # sort by RC

    if export_csv:
        export_changes_as_csv(changes, export_csv)

    for change in changes:
        print(','.join([change[field] for field in ['url', 'teams', 'next_tag', 'title']]))


@click.command(context_settings=CONTEXT_SETTINGS, short_help="Prints some release stats we want to track")
@click.option('--from-ref', '-f', help="Reference to start stats on (first RC tagged)", required=True)
@click.option('--to-ref', '-t', help="Reference to end stats at (current RC/final tag)", required=True)
@click.option('--release-milestone', '-r', help="Github release milestone", required=True)
@click.pass_context
def report(ctx, from_ref, to_ref, release_milestone):

    agent_release = Release.from_github(ctx, 'datadog-agent', release_milestone, from_ref=from_ref, to_ref=to_ref)
    integrations_release = Release.from_github(
        ctx, 'integrations-core', release_milestone, from_ref=from_ref, to_ref=to_ref
    )

    print('Release Branch:', agent_release.release_version)
    print('Release candidates:', len(agent_release.rc_tags))
    print('Number of Commits (datadog-agent):', len(agent_release.commits))
    print('Number of Commits (integrations-core):', len(integrations_release.commits))
    print('Release time in days:', agent_release.release_duration_days())
