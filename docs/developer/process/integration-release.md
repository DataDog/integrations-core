# Integration release

-----

Each Agent integration has its own release cycle. Many integrations are actively developed and released often while
some are rarely touched (usually indicating feature-completeness).

## Versioning

All releases adhere to [Semantic Versioning][semver-home].

Tags in the form `<INTEGRATION_NAME>-<VERSION>` [are added](../meta/cd.md) to the Git repository. Therefore, it's
possible to checkout and build the code for a certain version of a specific check.

## Setup

[Configure](../ddev/configuration.md#github) your GitHub auth.

## Identify changes

!!! note
    If you already know which integration you'd like to release, skip this section.

To see all checks that need to be released, run `ddev release show ready`.

1. Checkout and pull the most recent version of the `master` branch.

    ```
    git checkout master
    git pull
    ```

    !!! danger "Important"
        Not using the latest version of `master` may cause errors in the [build pipeline](../meta/cd.md).

2. Review which PRs were merged in between the latest release and the `master` branch.

    ```
    ddev release show changes <INTEGRATION>
    ```

    You should ensure that PR titles and changelog labels are correct.

## Creating the release

1. Create a release branch from master (suggested naming format is `<USERNAME>/release-<INTEGRATION_NAME>`).
   This has the purpose of opening a PR so others can review the changelog.

    !!! danger "Important"
        It is critical the branch name is not in the form `<USERNAME>/<INTEGRATION_NAME>-<NEW_VERSION>` because one of
        our Gitlab jobs is triggered whenever a Git reference matches that pattern, see !3843 & !3980.

2. Make the release.

    ### Core

    ```
    ddev release make <INTEGRATION>
    ```

    You may need to touch your Yubikey multiple times.

    This will automatically:

    * update the version in `<INTEGRATION>/datadog_checks/<INTEGRATION>/__about__.py`
    * update the changelog
    * update the `requirements-agent-release.txt` file
    * update [in-toto metadata](../meta/cd.md)
    * commit the above changes

    ### Third party

    * Update the version on `datadog_checks/<INTEGRATION>/__about__.py`.
    
    * Update the CHANGELOG.md file This file can be automatically updated by `ddev` using the following command:
    
    ```
    ddev release changelog <INTEGRATION_NAME> <VERSION>
    ``` 

    This command will list all merged PRs since the last release and creates a changelog entry based on the pull request labels,
    this means that *the version bump needs to be on a separate PR from the one that included the changes*.
    For changelog types, we adhere to those defined by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/#how).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |


3. Push your branch to GitHub and create a pull request.

    1. Update the title of the PR to something like `[Release] Bumped <INTEGRATION> version to <VERSION>`.
    1. Ask for a review in Slack.

4. Merge the pull request after approval or wait for it to be merged.

## Metadata

You need to run certain backend jobs if any changes modified integration metadata or assets such as dashboards.
If you are a contributor a datadog employee will handle this.

## Bulk releases (core integrations only)

To create a release for every integration that has changed, use `all` as the integration name in the `ddev release make`
step above.

```
ddev release make all
```

You may also pass a comma-separated list of checks to skip using the `--exclude` option, e.g.:

```
ddev release make all --exclude datadog_checks_dev
```

Note: releasing `all` will update the `.in-toto` file to include every integration, not just the changed integrations. This may result in an unnecessarily large `.in-toto` file if only releasing a few integrations.

!!! warning
    There is a known GitHub limitation where if an issue has too many labels (100), its state cannot be modified.
    If you cannot merge the pull request:

    1. Run the [remove-labels](../ddev/cli.md#ddev-meta-scripts-remove-labels) command
    1. After merging, manually add back the `changelog/no-changelog` label

Another option for bulk releases is selectively choosing the integrations to release. For example, if you are just releasing `check1` and `check2`: 

```
ddev release make check1 check2
```

## Betas (core integrations only)

Creating pre-releases follows the same workflow except you do not open a pull request but rather release directly from a branch.

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

### Core integrations

To bump a new core integration to `1.0.0` if it is not already there, run:

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

### Third party integrations

For first time releases of third party integrations, simply merge the integration to master and a release will be 
triggered with the specified version number in the about file.


## Base package releases

If you released `datadog_checks_base` or `datadog_checks_dev` then these must be uploaded to [PyPI][]
for use by [integrations-extras][].

This is automatically handled by two GitHub Action jobs: [release-base.yml][] and [release-dev.yml][].

In case you need to do it manually:

```
ddev release upload datadog_checks_[base|dev]
```

## Troubleshooting

#### Error signing with Yubikey
- If you encounter errors when signing with your Yubikey, ensure you ran `gpg --import <YOUR_KEY_ID>.gpg.pub`.
- If you receive this error when signing with your Yubikey, check if you have more than one Yubikey inserted in your computer. Try removing the Yubikey that's not used for signing and try signing again.
    
  ```
      File "/Users/<USER>/.pyenv/versions/3.9.4/lib/python3.9/site-packages/in_toto/runlib.py", line 529, in in_toto_run
        securesystemslib.formats.KEYID_SCHEMA.check_match(gpg_keyid)
      File "/Users/<USER>/.pyenv/versions/3.9.4/lib/python3.9/site-packages/securesystemslib/schema.py", line 1004, in check_match
        raise exceptions.FormatError(
    securesystemslib.exceptions.FormatError: '[none]' did not match 'pattern /[a-fA-F0-9]+$/'
  ```
    
#### Build pipeline failed

After merging the release PR, the [build pipeline](../meta/cd.md) can fail under a few cases. See below for steps on diagnosing the error and the corresponding fix.

- A file in the pull request was modified without re-signing. View the `Files Changed` tab in the recently merged release PR and verify the `.in-toto/tag.<KEYID>.link` exists and the integration files were signed.

  To resolve this, you'll need to bootstrap metadata for every integration:

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
    
- If a feature PR conflicting with the release PR is merged out of order.

    The following is a possible sequence of events that can result in the build pipeline failing:
    
        1. A release PR is opened
        2. A feature PR is opened and merged
        3. The release PR is merged after the feature PR.
        4. The release PR will not have updated and signed the feature PR's files, the released wheel will also not contain the changes from the feature PR.
  
    You may see an error like so:
    
    ```text
    in_toto.exceptions.RuleVerificationError: 'DISALLOW *' matched the following artifacts: ['/shared/integrations-core/datadog_checks_dev/datadog_checks/dev/tooling/commands/ci/setup.py']
    ```
      
    1. Verify whether the hash signed in `.in-toto/tag.<KEYID>.link`, [(see example)](https://github.com/DataDog/integrations-core/blob/9836c71f15a0cb93c63c1d2950dcdc28b49479a7/.in-toto/tag.57ce2495.link) matches what's on `master` for the artifact in question.
        
        To see the hash for the artifact, run the following `shasum` command (replace local file path):
        
        ```
        shasum -a 256 datadog_checks_dev/datadog_checks/dev/tooling/commands/ci/setup.py
        ```
    
    1. If any artifact mismatches, check out and pull the most recent version of the `master` branch.
    
        ```
        git checkout master
        git pull
        ```
            
    1. Release the integration again with a new version, bump the version appropriately.
    
        ```
        ddev release make <INTEGRATION> --version <VERSION>
        ```
    
    1. Verify that the integration files are signed, and update the integration changelog to reflect the feature PR title in the following format.
        
        ```
        * [<Changelog label>] <PR Title>. [See #<PR Number>](<Github PR link>).
        ```
       
    1. After approval, merge PR to master for a new build to be triggered.
  

## Releasers

For whom it may concern, the following is a list of GPG public key fingerprints known to correspond to developers
who, at the time of writing (27-09-2021), can trigger a build by signing [in-toto metadata](../meta/cd.md).

??? info "[Christine Chen](https://api.github.com/users/ChristineTChen/gpg_keys)"
    - `57CE 2495 EA48 D456 B9C4  BA4F 66E8 2239 9141 D9D3`
    - `36C0 82E7 38C7 B4A1 E169  11C0 D633 59C4 875A 1A9A`

??? info "[Paul Coignet](https://api.github.com/users/coignetp/gpg_keys)"
    - `024E 42FE 76AD F19F 5D57  7503 07E5 2EA3 88E4 08FD`
    - `1286 0553 D1DC 93A7 2CD1  6956 2D98 DCE7 FBFF C9C2`

??? info "[Dave Coleman](https://api.github.com/users/dcoleman17/gpg_keys)"
    - `8278 C406 C1BB F1F2 DFBB  5AD6 0AE7 E246 4F8F D375`
    - `98A5 37CD CCA2 8DFF B35B  0551 5D50 0742 90F6 422F`

??? info "[Greg Marabout Demazure](https://api.github.com/users/gmarabout/gpg_keys)"
    - `01CC 90D7 F047 93D4 30DF  9C7B 825B 84BD 1EE8 E57C`
    - `C719 8925 CAE5 11DE 7FC2  EB15 A9B3 5A96 7570 B459`

??? info "[Paola Ducolin](https://api.github.com/users/pducolin/gpg_keys)"
    - `EAC5 F27E C6B1 A814 1222  1942 C4E1 549E 937E F5A2`
    - `A40A DD71 41EB C767 BBFB  E0B8 9128 2E2F E536 C858`

??? info "[Fanny Jiang](https://api.github.com/users/fanny-jiang/gpg_keys)"
    - `BB47 F8E8 8908 168B CAE4  324A D9C3 43B4 D73F BE12`
    - `800C 2BA9 A7AA 4F84 DD39  A558 4306 7845 F282 FB96`

??? info "[Ofek Lev](https://api.github.com/users/ofek/gpg_keys)"
    - `C295 CF63 B355 DFEB 3316  02F7 F426 A944 35BE 6F99`
    - `D009 8861 8057 D2F4 D855  5A62 B472 442C B7D3 AF42`

??? info "[Julia Simon](https://api.github.com/users/hithwen/gpg_keys)"
    - `0244 AAA8 DD1E FE47 30A4  F1CA 392C 882E 0DA0 C6C8`
    - `129A 26CF A726 3C85 98A6  94B0 8659 1366 CBA1 BF3C`

??? info "[Florian Veaux](https://api.github.com/users/FlorianVeaux/gpg_keys)"
    - `3109 1C85 5D78 7789 93E5  0348 9BFE 5299 D02F 83E9`
    - `7A73 0C5E 48B0 6986 1045  CF8B 8B2D 16D6 5DE4 C95E`

??? info "[Sarah Witt](https://api.github.com/users/sarah-witt/gpg_keys)"
    - `47C5 A022 73F1 CF81 04EE  8D1A 7A67 DC43 B24C 1542`
    - `0620 14C0 3FC0 44E5 F029  32A2 E50E CC57 6463 4BC1`

??? info "[Alexandre Yang](https://api.github.com/users/AlexandreYang/gpg_keys)"
    - `FBC6 3AE0 9D0C A9B4 584C  9D7F 4291 A11A 36EA 52CD`
    - `F8D9 181D 9309 F8A4 957D  636A 27F8 F48B 18AE 91AA`

??? info "[Andrew Zhang](https://api.github.com/users/yzhan289/gpg_keys)"
    - `EABC A4AC 14AC BAF0 06CC  0384 7C67 39CB 3A79 9F86`
    - `0149 2127 FC6E 1A4C 900B  78DA ED58 C98E BC9C C677`
