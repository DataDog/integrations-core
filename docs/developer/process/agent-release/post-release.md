# Post release

-----

## Finalize

On the day of the final stable release, [tag](#tag) the [branch](#branch) with `<MAJOR>.<MINOR>.0`.

After the main Agent release manager confirms successful deployment to a few targets, create a branch based on `master` and run:

```
ddev agent changelog
ddev agent integrations
```

See more options for [`ddev agent changelog`](../../ddev/cli.md#changelog) and [`ddev agent integrations`](../../ddev/cli.md#integrations).

Run the following commands to update the contents:

1. `ddev agent changelog -w -f` to update the existing [`AGENT_CHANGELOG`][agent-changelog] file
2. `ddev agent integrations -w -f` to update the existing [`AGENT_INTEGRATIONS`][agent-integrations] file.

Create a pull request and wait for approval before merging.


## Patches

!!! important
    Only critical fixes are included in patches. See definition for
    [critical fixes](https://github.com/DataDog/datadog-floss-guidance/blob/master/docs/severity.md#critical).

Releases after the final Agent release should be reserved for critical issues only. Cherry-picking commits and releases for
 the patch release is mostly similar to the process for [preparing release candidates](agent-release.md#release-candidates).

However, it's possible that from the time [code freeze ended](agent-release.md#release-week),
the integration has other non-critical commits or was released.
The next section will describe the process for preparing the patch release candidates.

### Multiple check releases between bugfix release



