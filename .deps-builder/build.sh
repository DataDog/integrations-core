# Script to run inside builder image
set -ex

omnibus_project=python-dependencies
root=${INTEGRATIONS_CORE_PATH:-/integrations-core}

cd ${root}/.deps-builder/omnibus
bundle install
bundle exec omnibus build ${omnibus_project} --log-level=debug
