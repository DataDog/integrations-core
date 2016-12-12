require 'ci/common'

def kafka_consumer_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

namespace :ci do
  namespace :kafka_consumer do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('kafka_consumer/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml up -d)
      Wait.for 2181
      Wait.for 9092
      sleep_for 5
      sh %(docker run -d --name kafka_producer -v /var/run/docker.sock:/var/run/docker.sock -e HOST_IP=172.17.0.1 -e ZK=172.17.0.1:2181 -i -t wurstmeister/kafka /bin/bash -c '$KAFKA_HOME/bin/kafka-console-producer.sh --topic=test --broker-list=`broker-list.sh` < /etc/group')
      sh %(docker run -d --name kafka_consumer -v /var/run/docker.sock:/var/run/docker.sock -e HOST_IP=172.17.0.1 -e ZK=172.17.0.1:2181 -i -t wurstmeister/kafka /bin/bash -c '$KAFKA_HOME/bin/kafka-console-consumer.sh --topic=test --zookeeper=$ZK --consumer-property group.id=my_consumer ')
    end

    task before_script: ['ci:common:before_script'] do
      sleep_for 30
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'kafka_consumer'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f kafka_consumer)
      sh %(docker rm -f kafka_producer)
      sh %(docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml stop)
      sh %(docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml rm -f)
    end

    task :execute do
      exception = nil
      begin
        %w(before_install install before_script).each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        Rake::Task["#{flavor.scope.path}:script"].invoke
        Rake::Task["#{flavor.scope.path}:before_cache"].invoke
      rescue => e
        exception = e
        puts "Failed task: #{e.class} #{e.message}".red
      end
      if ENV['SKIP_CLEANUP']
        puts 'Skipping cleanup, disposable environments are great'.yellow
      else
        puts 'Cleaning up'
        Rake::Task["#{flavor.scope.path}:cleanup"].invoke
      end
      raise exception if exception
    end
  end
end
