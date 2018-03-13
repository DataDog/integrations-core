from __future__ import print_function, unicode_literals
from invoke import task

# Note: these are the names of the folder containing the check
AGENT_BASED_INTEGRATIONS = [
    'datadog-checks-base',
    'disk',
    'envoy',
    'istio',
    'kube_proxy',
    'kubelet',
    'prometheus',
    'vsphere',
]

@task(help={
    'targets': "Comma separated names of the checks that will be tested",
    'changed-only': "Whether to only test checks that were changed in a PR",
    'dry-run': "Just print the list of checks that would be tested",
})
def test(ctx, targets=None, changed_only=False, dry_run=False):
    """
    Run the tests for Agent-based checks

    Example invokation:
        inv test --targets=disk,redisdb
    """
    if targets is None:
        targets = AGENT_BASED_INTEGRATIONS
    elif isinstance(targets, basestring):
        targets = [t for t in targets.split(',') if t in AGENT_BASED_INTEGRATIONS]

    if changed_only:
        targets = list(set(targets) & integrations_changed(ctx))

    if dry_run:
        print(targets)
        return

    for check in targets:
        with ctx.cd(check):
            print("\nRunning tox in '{}'\n".format(check))
            ctx.run('tox')

def integrations_changed(ctx):
    """
    Find out which checks were changed in the current branch
    """
    checks = set()
    res = ctx.run('git diff --name-only master...', hide='out')
    for line in res.stdout.split('\n'):
        if line:
            checks.add(line.split('/')[0])
    return checks
