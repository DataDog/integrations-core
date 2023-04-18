:: Only required on pull requests
if defined GITHUB_BASE_REF (
  git fetch origin master:master
)
