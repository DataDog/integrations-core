:: Only required on non-master branches
if "%GITHUB_REF_NAME%" NEQ "master" (
  git fetch origin master:master
)
