# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...console import CONTEXT_SETTINGS
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


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Prints the PRs merged between the first RC and the current RC/final build",
)
@click.option('--from-ref', '-f', help="Reference to start stats on (first RC tagged)", required=True)
@click.option('--to-ref', '-t', help="Reference to end stats at (current RC/final tag)", required=True)
@click.option('--release-milestone', '-r', help="Github release milestone", required=True)
@click.pass_context
def merged_prs(ctx, from_ref, to_ref, release_milestone):

    agent_release = Release.from_github(ctx, 'datadog-agent', release_milestone, from_ref=from_ref, to_ref=to_ref)
    integrations_release = Release.from_github(
        ctx, 'integrations-core', release_milestone, from_ref=from_ref, to_ref=to_ref
    )

    changes = [parse_commit(commit) for commit in agent_release.commits + integrations_release.commits]
    changes = sorted(changes, key=lambda x: x['next_tag'])  # sort by RC
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
