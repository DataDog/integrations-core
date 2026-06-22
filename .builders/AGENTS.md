# Builder Image Guidelines

## Pinning Downloaded Tooling

Every external artifact fetched in a Dockerfile or setup script must specify both
an exact version and a SHA-256 hash. Do not download "latest" or an unverified
file.

- Define the version in an `ENV ..._VERSION` (or `ARG`) so it is visible and
  reusable.
- On Windows, fetch with `Get-RemoteFile -Uri ... -Path ... -Hash '<sha256>'`
  (see `images/helpers.ps1`). The hash is mandatory for these downloads.
- On Linux, verify with `echo "<sha256>  <file>" | sha256sum --check` (or the
  `SHA256=` argument to `install-from-source.sh`).

Existing entries (7-Zip, Git, Rust, Python, OpenSSL, NASM, Perl, PostgreSQL,
etc.) all follow this pattern; match it for anything new.

## Pinning Python Dependencies

Pin Python packages to exact versions with `==`:

- In the requirement files (`deps/*.txt`, `images/runner_dependencies.txt`,
  `test_dependencies.txt`), add new entries as `name==X.Y.Z`. Bounded ranges
  (e.g. `cryptography<49`) are acceptable only when a transitive constraint
  requires it; add a comment explaining why.
- In inline `pip install` commands inside a Dockerfile, pin every package
  (e.g. `pip install meson==1.11.1 ninja==1.13.0`), never a bare package name.
