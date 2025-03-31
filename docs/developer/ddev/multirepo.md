# Working with multiple repositories and configurations

The `ddev` CLI utilizes a central configuration file typically located in your user configuration directory. However, managing configurations across different projects (like `integrations-core`, `integrations-extras`, or Agent repositories) or even different [worktrees](https://git-scm.com/docs/git-worktree) within the same repository can sometimes require specific settings, especially for the `repo` variable.

To simplify this, `ddev` supports local configuration overrides using a `.ddev.toml` file.

## Local Configuration Overrides

When you run a `ddev` command, it searches for a `.ddev.toml` file in the current working directory and its parent directories. If found, `ddev` merges the settings from this local file with the global `config.toml`.

**Key aspects:**

*   **Override Mechanism:** Settings defined in `.ddev.toml` take precedence over the same settings in the global `config.toml`. Settings unique to either file are combined.
*   **Discovery:** `ddev` automatically finds the closest `.ddev.toml` by traversing up the directory tree from your current location.
*   **Use Case:** Ideal for setting a specific `repo` path for a project checkout, managing different worktrees of the same repository, or defining other project-specific configurations without altering the global settings.

## Command Behavior with Overrides

The presence of a `.ddev.toml` file influences how certain `ddev` config commands behave. Assume the global config has `repo = "core"` and `org = "default"`, and a local `.ddev.toml` has `repo = "local-override"` and `github.user = "test-user"`.

*   **`ddev config show`**: Displays the merged configuration, annotating each setting with its source (`GlobalConfig:<line>` or `Overrides:<line>`).

    *Example:*
    ```bash
    $ ddev config show
    repo = "local-override"       # Overrides:1
    org = "default"               # GlobalConfig:3
    [github]                      # Overrides:2
    user = "test-user"            # Overrides:3
    ```

*   **`ddev config set <KEY> <VALUE> [--overrides]`**: Use the `--overrides` flag to modify or add a setting in the `.ddev.toml` file. Without the flag, it modifies the global `config.toml`. If `--overrides` is used and no `.ddev.toml` exists in the current directory, `ddev` prompts for creation.

    *Example (modify local override):*
    ```bash
    $ ddev config set github.user different-user --overrides
    New setting:

    [github]
    user = "different-user"
    ```
    *Example (modify global):*
    ```bash
    $ ddev config set org new-org
    New setting:

    org = "new-org"
    ```

*   **`ddev config edit [--overrides]`**: Opens the configuration file in your default editor. With `--overrides`, it opens the discovered `.ddev.toml`; otherwise, it opens the global `config.toml`. Aborts if `--overrides` is used but no `.ddev.toml` is found.

*   **`ddev config find`**: Displays the path to the global `config.toml`. If overrides are active, it also indicates the path to the applied `.ddev.toml`.

    *Example (overrides active):*
    ```bash
    $ ddev config find
    /Users/you/.config/ddev/config.toml
    ----- Overrides applied from .ddev.toml
    ```
    *Example (no overrides):*
    ```bash
    $ ddev config find
    /Users/you/.config/ddev/config.toml
    ```

*   **`ddev config local-repo`**: A shortcut command to quickly configure the current directory as a local repository override. It creates (or updates) a `.ddev.toml` file in the current working directory, setting `repos.local` to the current path and setting the active `repo` to `local`. This is useful for initializing overrides for a specific project checkout or worktree.

    *Example:*
    ```bash
    # In /path/to/your/project
    $ ddev config local-repo
    Local repo configuration added in .ddev.toml
    Local config content:

    repo = "local"

    [repos]
    local = "/path/to/your/project"

    ```

By leveraging `.ddev.toml` files, you can maintain distinct configurations for different projects or worktrees seamlessly, improving your workflow when switching contexts.
