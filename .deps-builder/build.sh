# Script to run inside builder image
set -ex

omnibus_project=python-dependencies
cd /integrations-core/.deps-builder/omnibus
bundle install
PACKAGE_VERSION=$(git rev-parse --short HEAD) \
               bundle exec omnibus build ${omnibus_project}
