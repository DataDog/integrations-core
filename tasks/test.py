# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os
import sys

from invoke import task
from invoke.exceptions import Exit

from .constants import AGENT_BASED_INTEGRATIONS, ROOT


def files_changed(ctx):
    """
    Return the list of file changed in the current branch compared to `master`
    """
    return ctx.run('git diff --name-only master...', hide='out').stdout


def run_tox(ctx, target, bench, dry_run):
    """
    Run tox on the folders contained in `targets`
    """
    with ctx.cd(target):
        if dry_run:
            sys.stdout.write("\nRunning tox in '{}'...\n".format(target))
            sys.stdout.write("Ok.\n")
        else:
            env_list = ctx.run('tox --listenvs', hide='out').stdout
            env_list = [e.strip() for e in env_list.splitlines()]

            if bench:
                benches = [e for e in env_list if e.startswith('bench')]
                # Don't print anything if there are no benchmarks
                if benches:
                    ctx.run('tox -e {}'.format(benches[0]))
            else:
                sys.stdout.write('\nRunning tox in `{}`...\n'.format(target))
                ctx.run('tox -e {}'.format(','.join(e for e in env_list if not e.startswith('bench'))))
                sys.stdout.write('Ok.\n')


def check_requirements(ctx, target, dry_run, changed_files):
    """
    Assert the output of pip-compile is the same as the contents of
    `requirements.txt` for the given check
    """
    target_path = os.path.join(ROOT, target)
    if not os.path.exists(target_path):
        raise Exit("Unable to find folder '{}'".format(target_path))

    sys.stdout.write("\nVerifying requirements are in sync for '{}'...\n".format(target))

    if not dry_run:
        # Check the files are there
        req_in = os.path.join(target_path, 'requirements.in')
        req_txt = os.path.join(target_path, 'requirements.txt')
        if not (os.path.exists(req_in) and os.path.exists(req_txt)):
            raise Exit("Target folder '{}' must contain 'requirements.in' and 'requirements.txt'\n".format(target_path))

        # Skip if the files didn't change
        if changed_files and not (req_in in changed_files and req_txt in changed_files):
            sys.stdout.write("Skip, requirements didn't change.\n")
            return

        # Get the output of pip-compile
        with ctx.cd(target_path):
            out = ctx.run("pip-compile -n --generate-hashes", hide=True).stdout

        # Read the contents of `requirements.txt`
        with open(req_txt) as f:
            if f.read() != out:
                msg = "'requirements.in' and 'requirements.txt' are out of sync, please run pip-compile and try again\n"
                raise Exit(msg)

    sys.stdout.write("Ok.\n")


@task(help={
    'targets': "Comma separated names of the checks that will be tested",
    'changed-only': "Whether to only test checks that were changed in a PR",
    'bench': "Runs any benchmarks",
    'dry-run': "Runs the task without actually doing anything",
})
def test(ctx, targets=None, changed_only=False, bench=False, dry_run=False):
    """
    Run the tests for Agent-based checks

    Example invocation:
        inv test --targets=disk,redisdb
    """
    if targets is None:
        targets = AGENT_BASED_INTEGRATIONS
    elif isinstance(targets, basestring):
        targets = [t for t in targets.split(',') if t in AGENT_BASED_INTEGRATIONS]

    # get the list of the files that changed compared to `master`
    changed_files = []
    if changed_only:
        changed_files = files_changed(ctx).split('\n')
        changed_checks = set()
        for line in changed_files:
            if line:
                changed_checks.add(line.split('/')[0])
        targets = list(set(targets) & changed_checks)

    if bench:
        sys.stdout.write('\nRunning available benchmarks...\n')

    for target in targets:
        # check requirements.in and requirements.txt are in sync
        if not bench:
            check_requirements(ctx, target, dry_run, changed_files)
        # run the tests for each target with tox
        run_tox(ctx, target, bench, dry_run)
