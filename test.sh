CHECKS=$(ls)

export VOLATILE_DIR='/tmp/integration-sdk-testing'
export CONCURRENCY='2'
export RUN_VENV=true
export SDK_TESTING=true
export INTEGRATIONS_DIR='/home/vagrant/integrations-core/embedded'
export TRAVIS_BUILD_DIR='/home/vagrant/integrations-core'
export SDK_HOME='/home/vagrant/integrations-core'

# for CHECK in $CHECKS; do
#   venv/bin/nosetests -s -v -A "(not requires) and not windows" "/home/vagrant/integrations-core/$CHECK/test_$CHECK.py"
# done
nosetests -s -v -A "(not requires) and not windows" "/home/vagrant/integrations-core/activemq/test_activemq.py"
