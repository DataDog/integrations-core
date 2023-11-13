set omnibus_project=python-dependencies
set PACKAGE_VERSION=0.0.1
cd %~p0\omnibus

REM Execute omnibus
bundle install && bundle exec omnibus build %omnibus_project% --log-level=debug

