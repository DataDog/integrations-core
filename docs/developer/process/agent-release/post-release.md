# Post release

-----

## Finalize

On the day of the final stable release, [tag](pre-release.md#tag) the [branch](pre-release.md#branch) with `<MAJOR>.<MINOR>.0`.

After the main Agent release manager confirms successful deployment to a few targets, create a branch based on `master` and run:

```
ddev agent changelog
ddev agent integrations
```

See more options for [`ddev agent changelog`](../../ddev/cli.md#ddev-agent-changelog) and
[`ddev agent integrations`](../../ddev/cli.md#ddev-agent-integrations).

Run the following commands to update the contents:

1. `ddev agent changelog -w -f` to update the existing [`AGENT_CHANGELOG`][agent-changelog] file
2. `ddev agent integrations -w -f` to update the existing [`AGENT_INTEGRATIONS`][agent-integrations] file.
3. `ddev agent integrations-changelog -w` to add Agent version to existing `CHANGELOG.md` releases of integrations.

Create a pull request and wait for approval before merging.

## Patches

!!! important
    Only critical fixes are included in patches. See definition for
    [critical fixes](https://github.com/DataDog/datadog-floss-guidance/blob/master/docs/severity.md#critical).

Releases after the final Agent release should be reserved for critical issues only. Cherry-picking commits and releases for
 the patch release is mostly similar to the process for [preparing release candidates](pre-release.md#release-candidates).

However, it's possible that from the time [code freeze ended](pre-release.md#release-week) and a bugfix is needed,
the integration has other non-critical commits or was released.

Given the effort of QA-ing the Agent release, any new changes should be _carefully_ selected and included for the patch.

The next section will describe the process for preparing the patch release candidates.

### Multiple check releases between bugfix release

There are two main cases where the release manager will have to release integrations off of the release branch: the freeze has lifted and changes to an integration have been merged after freeze and before a bugfix for an RC, or a [patch release](#patches) is required. To release an integration off of the release branch, perform the following steps:

1. Cherry-pick the bugfix commit to the [release branch](pre-release.md#branch).
2. Release the integration.
    - Create a branch based off of the release branch. 
    - Run the [integration release](../integration-release.md#new-integrations) command on that branch.
    - Make a pull request with that branch, then merge it to the release branch.
    - Note: if there are multiple integrations to release, do not use `ddev release make all --exclude <INTGS>`. Once `master` is unfrozen, releasing `all` may result in unwanted and unshipped changes to the release branch if new changes are introduced. Use `ddev release make check1 check2` instead if releasing `check1` and `check2`.

    !!! important
        Remember to trigger the release pipeline and build the wheel. You can do so by [tagging the release](../../ddev/cli.md#ddev-release-tag):

            `ddev release tag <INTEGRATION>`

        Note: only release PRs merged to master automatically build a wheel.


3. Then pull the latest release branch so your branch has both the bugfix commit and release commit.

4. [Tag](pre-release.md#tag) the branch with the new bumped version `<MAJOR>.<MINOR>.<PATCH>-rc.1`.

5. After the release has been made, make a PR to `master` with the updates to `CHANGELOG.md`, [agent release requirements](https://github.com/DataDog/integrations-core/blob/master/requirements-agent-release.txt), and `__about__.py` of the integrations that were released on the release branch. Do not include the change to the in-toto file. If the current version of `__about__.py` is higher on master than the release branch, then **only** update the `CHANGELOG.md` in this PR.

    !!! important
        Do not merge this PR unless the release tag from the previous PR has been pushed or the release pipeline will incorrectly attempt to release from `master`.

6. Finally, if a patch release was performed, follow the same steps to [finalize the release](#finalize).
