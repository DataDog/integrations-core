@echo on

:: 1. Check if the repo is shallow by capturing the output of the git command
FOR /F "tokens=*" %%g IN ('git rev-parse --is-shallow-repository') do (SET IS_SHALLOW=%%g)

:: 2. If it is shallow ("true"), fetch the full history
IF "%IS_SHALLOW%"=="true" (
  ECHO Repository is shallow. Unshallowing to get full history...
  git fetch --unshallow --tags -f origin
)

:: 3. Only required on non-master branches (Your original logic)
if "%GITHUB_REF_NAME%" NEQ "master" (
  git fetch origin master:master
)