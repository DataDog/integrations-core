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
  (e.g. `pip install meson==$Env:MESON_VERSION ninja==$Env:NINJA_VERSION`),
  never a bare package name.

## Keeping Pins Up To Date

Pins in the builder images are tracked by Renovate (the `build dependencies`
group in `renovate.json`) so they don't rot. For a version to be trackable:

- Hoist it into its own `ENV NAME="X.Y.Z"` declaration and reference it from the
  `RUN` step (`$Env:NAME` under `pwsh`, `${NAME}` under bash). A `# renovate:`
  comment cannot live mid-`RUN` because line continuations break it, so the
  annotation must sit on the line directly above the `ENV`.
- Annotate the `ENV` with the datasource and package name on the preceding line:

```dockerfile
# renovate: datasource=pypi depName=meson
ENV MESON_VERSION="1.11.1"
```

The matcher lives in `renovate.json` under `customManagers` (scoped to the
builder Dockerfiles under `.builders/images/`). It currently covers the `pypi`
datasource; extend it there when adding pins from other ecosystems.
