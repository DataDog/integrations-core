# The GitHub PRs listing tool
IMPORTANT: for this project we want the plan to be written in `/tmp/plan.md`, not in the output directory of the project.

We want to build a CLI tool using typer that allows us to list a given number of PRs from a given repository.

The cli should contain the following arguments:
- `repo`: argument that contains the `owner/repo` we want to use
- `-n`: the number of PRs we want to list. Default is 10.


The output of the tool should be the list of `n` open PRs sorted by creation date, showing the most recent PRs first.

## Accesing GitHub

The call to github should be de asynchronously using the github api. We need a github client that uses httpx and that supports the following endpoints:

- list prs: this is needed to get the list of open PRs froma given repository.
- get user: we will need this to know the company the user is in, if any
- list pull request files: we want to have some statistics of the number of files that have been modified.

You need to take into accoutn that we might have pagination in the list pull requests  endpoint. Make sure to implement pagination if the number of pages requested is greater than the maximum number of elements per page (100).

If any endpoint is needed for the output described below and is missing in the list, include it as well in the async client.

## Output

For each PR, I want to have the following output (written as a rich table):

- **PR Number**: The standard PR identifier (e.g., #1347).
- **Title**: The title of the pull request.
- **Author & Company**: The GitHub username of the author, alongside the `company` they work for (if specified in their public profile).
- **Mergeable Status**: A clear indicator of whether the PR currently has merge conflicts (`clean`, `dirty`, etc.).
- **Size (+/-)**: The exact number of line `additions` and `deletions` in the PR.
- **File Status Breakdown**: A count of the specific file statuses within the PR (e.g., "2 added, 1 modified, 0 removed").
- **Approval State**: The current review status of the PR (e.g., `APPROVED`, `CHANGES_REQUESTED`, or `PENDING`).
