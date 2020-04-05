# Integration release

-----

Each Agent integration has its own release cycle. Many integrations are actively developed and released often while
some are rarely touched (usually indicating feature-completeness).

## Versioning

All releases adhere to [Semantic Versioning](https://semver.org).

Tags in the form `<INTEGRATION_NAME>-<VERSION>` [are added](../meta/cd.md) to the Git repository. Therefore, it's
possible to checkout and build the code for a certain version of a specific check.

## Setup

[Configure](../ddev/configuration.md#github) your GitHub auth.

## Identify changes

!!! note
    If you already know which integration you'd like to release, skip this section.

To see all checks that need to be released, run `ddev release show ready`.

## Steps

1. Checkout and pull the most recent version of the `master` branch.

    ```
    git checkout master
    git pull
    ```

    !!! danger "Important"
        Not using the latest version of `master` may cause errors in the [build pipeline](../meta/cd.md).

1. Review which PRs were merged in between the latest release and the `master` branch.

    ```
    ddev release show changes <INTEGRATION>
    ```

    You should ensure that PR titles and changelog labels are correct.

1. Create a release branch from master (suggested naming format is `<USERNAME>/release-<INTEGRATION_NAME>`).
   This has the purpose of opening a PR so others can review the changelog.

    !!! danger "Important"
        It is critical the branch name is not in the form `<USERNAME>/<INTEGRATION_NAME>-<NEW_VERSION>` because one of
        our Gitlab jobs is triggered whenever a Git reference matches that pattern, see !3843 & !3980.

1. Make the release.

    ```
    ddev release make <INTEGRATION>
    ```

    You may need to touch your Yubikey multiple times.

    This will automatically:

    - update the version in `<INTEGRATION>/datadog_checks/<INTEGRATION>/__about__.py`
    - update the changelog
    - update the `requirements-agent-release.txt` file
    - update [in-toto metadata](../meta/cd.md)
    - commit the above changes

1. Push your branch to GitHub and create a pull request.

    1. Update the title of the PR to something like `[Release] Bumped <INTEGRATION> version to <VERSION>`.
    1. Ask for a review in Slack.

1. Merge the pull request after approval.

### PyPI

If you released `datadog_checks_base` or `datadog_checks_dev` then you will need to upload to [PyPI](https://pypi.org)
for use by [integrations-extras](https://github.com/DataDog/integrations-extras).

```
ddev release upload datadog_checks_[base|dev]
```

### Metadata

You need to run certain jobs if any changes modified integration metadata. See the
[Declarative Integration Pipeline](https://github.com/DataDog/devops/wiki/Declarative-Integration-Pipeline) wiki.

## Bulk releases

To create a release for every integration that has changed, use `all` as the integration name in the `ddev release make`
step above.

```
ddev release make all
```

You may also pass a comma-separated list of checks to skip using the `--exclude` option, e.g.:

```
ddev release make all --exclude datadog_checks_dev
```

!!! warning
    There is a known GitHub limitation where if an issue has too many labels (100), its state cannot be modified.
    If you cannot merge the pull request:

    1. Run the [remove-labels](../ddev/cli.md#remove-labels) command
    1. After merging, manually add back the `changelog/no-changelog` label

## Betas

Creating pre-releases is the same workflow except you do not open a pull request but rather release directly from a branch.

In the `ddev release make` step set `--version` to `[major|minor|patch],[rc|alpha|beta]`.

For example, if the current version of an integration is `1.1.3`, the following command will bump it to `1.2.0-rc.1`:

```
ddev release make <INTEGRATION> --version minor,rc
```

After pushing the release commits to GitHub, run:

```
ddev release tag <INTEGRATION>
```

This manually triggers the [build pipeline](../meta/cd.md).

To increment the version, omit the first part, e.g.:

```
ddev release make <INTEGRATION> --version rc
```

## New integrations

To bump a new integration to `1.0.0` if it is not already there, run:

```
ddev release make <INTEGRATION> --new
```

To ensure this for all integrations, run:

```
ddev release make all --new
```

If a release was created, run:

```
ddev agent requirements
```

## Troubleshooting

- If you encounter errors when signing with your Yubikey, ensure you ran `gpg --import <YOUR_KEY_ID>.gpg.pub`.
- If the [build pipeline](../meta/cd.md) failed, it is likely that you modified a file in the pull request
  without re-signing. To resolve this, you'll need to bootstrap metadata for every integration:

    1. Checkout and pull the most recent version of the `master` branch.

        ```
        git checkout master
        git pull
        ```

    1. Sign everything.

        ```
        ddev release make all --sign-only
        ```

        You may need to touch your Yubikey multiple times.

    1. Push your branch to GitHub.
    1. Manually trigger a build.

        ```
        git tag <USERNAME>bootstrap-1.0.0 -m <USERNAME>bootstrap-1.0.0
        ```

        The tag name is irrelevant, it just needs to look like an integration release. Gitlab doesn't sync
        deleted tags, so any subsequent manual trigger tags will need to increment the version number.

    1. Delete the branch and tag, locally and on GitHub.

## Releasers

For whom it may concern, the following is a list of GPG public key fingerprints known to correspond to developers
who, at the time of writing (28-02-2020), can trigger a build by signing [in-toto metadata](../meta/cd.md).

??? info "[Christine Chen](https://api.github.com/users/ChristineTChen/gpg_keys)"
    - `57CE 2495 EA48 D456 B9C4  BA4F 66E8 2239 9141 D9D3`
    - `36C0 82E7 38C7 B4A1 E169  11C0 D633 59C4 875A 1A9A`

??? info "[Dave Coleman](https://api.github.com/users/dcoleman17/gpg_keys)"
    - `8278 C406 C1BB F1F2 DFBB  5AD6 0AE7 E246 4F8F D375`
    - `98A5 37CD CCA2 8DFF B35B  0551 5D50 0742 90F6 422F`

??? info "[Mike Garabedian](https://api.github.com/users/mgarabed/gpg_keys)"
    - `F90C 0097 67F2 4B27 9DC2  C83D A227 6601 6CB4 CF1D`
    - `2669 6E67 28D2 0CB0 C1E0  D2BE 6643 5756 8398 9306`

??? info "[Thomas Hervé](https://api.github.com/users/therve/gpg_keys)"
    - `59DB 2532 75A5 BD4E 55C7  C5AA 0678 55A2 8E90 3B3B`
    - `E2BD 994F 95C0 BC0B B923  1D21 F752 1EC8 F485 90D0`

??? info "[Ofek Lev](https://api.github.com/users/ofek/gpg_keys)"
    - `C295 CF63 B355 DFEB 3316  02F7 F426 A944 35BE 6F99`
    - `D009 8861 8057 D2F4 D855  5A62 B472 442C B7D3 AF42`

??? info "[Florimond Manca](https://api.github.com/users/florimondmanca/gpg_keys)"
    - `B023 B02A 0331 9CD8 D19A  4328 83ED 89A4 5548 48FC`
    - `0992 11D9 AA67 D21E 7098  7B59 7C7D CB06 C9F2 0C13`

??? info "[Julia Simon](https://api.github.com/users/hithwen/gpg_keys)"
    - `4A54 09A2 3361 109C 047C  C76A DC8A 42C2 8B95 0123`
    - `129A 26CF A726 3C85 98A6  94B0 8659 1366 CBA1 BF3C`

??? info "[Florian Veaux](https://api.github.com/users/FlorianVeaux/gpg_keys)"
    - `3109 1C85 5D78 7789 93E5  0348 9BFE 5299 D02F 83E9`
    - `7A73 0C5E 48B0 6986 1045  CF8B 8B2D 16D6 5DE4 C95E`

??? info "[Alexandre Yang](https://api.github.com/users/AlexandreYang/gpg_keys)"
    - `FBC6 3AE0 9D0C A9B4 584C  9D7F 4291 A11A 36EA 52CD`
    - `F8D9 181D 9309 F8A4 957D  636A 27F8 F48B 18AE 91AA`
