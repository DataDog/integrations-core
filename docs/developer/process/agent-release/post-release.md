# Post release

-----

## Finalize

On the day of the final stable release, [tag](pre-release.md#tag) the [branch](pre-release.md#branch) with `<MAJOR>.<MINOR>.0`.

After the main Agent release manager confirms successful deployment to a few targets, create a branch based on `master` and run:

```
ddev agent changelog
ddev agent integrations
```

See more options for [`ddev agent changelog`](../../ddev/cli.md#changelog) and [`ddev agent integrations`](../../ddev/cli.md#integrations).

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

The next section will describe the process for preparing the patch release candidates.

### Multiple check releases between bugfix release

Given the effort of QA-ing the Agent release, any new changes should be _carefully_ selected and included for the patch.

Follow the following steps to add patch release:

1. Cherry-pick the bugfix commit to the [release branch](pre-release.md#branch).
2. Release the integration on the release branch.
    - Make a pull request with [integration release](../integration-release.md#new-integrations), then merge it to the release branch.

    !!! important
        Remember to trigger the release pipeline and build the wheel. You can do so by [tagging the release](../../ddev/cli.md#tag):

            `ddev release tag <INTEGRATION>`

        Note: only release PRs merged to master automatically build a wheel.


3. Then pull the latest release branch so your branch has both the bugfix commit and release commit.

4. [Tag](pre-release.md#tag) the branch with the new bumped version `<MAJOR>.<MINOR>.<PATCH>-rc.1`.

5. When the patch release is ready, follow the same steps to [finalize the release](post-release.md#finalize).
Also manually update the changelog of the integrations that were released on the release branch, see [example](https://github.com/DataDog/integrations-core/pull/6617).
