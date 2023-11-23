set omnibus_project=python-dependencies
cd %~p0\omnibus

REM Execute omnibus
bundle install && bundle exec omnibus build %omnibus_project% --log-level=debug

