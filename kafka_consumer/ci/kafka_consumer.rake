require 'ci/common'

def kafka_consumer_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def kafka_consumer_options
  ENV['FLAVOR_OPTIONS'] || 'zookeeper'
end

namespace :ci do
  namespace :kafka_consumer do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('kafka_consumer')
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 CONSUMER_OFFSET_STORAGE=#{kafka_consumer_options} docker-compose -f \
           #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml up -d)
      Wait.for 2181
      Wait.for 9092
      wait_on_docker_logs('resources_kafka_1', 15, '[Kafka Server 1001], started')
      wait_on_docker_logs('resources_zookeeper_1', 15, 'NodeExists for /brokers/ids')
      sh %(EXTERNAL_PORT=9091 EXTERNAL_JMX_PORT=9998 CONSUMER_OFFSET_STORAGE=#{kafka_consumer_options} docker-compose -f \
           #{ENV['TRAVIS_BUILD_DIR']}/kafka/ci/resources/docker-compose-single-broker.yml scale kafka=2)
      wait_on_docker_logs('resources_kafka_2', 15, '[Kafka Server 1002], started')
    end

    task before_script: ['ci:common:before_script'] do
      # wait_on_docker_logs('resources_kafka_1', 15, 'Partition [test,0] on broker 1001')
      # wait_on_docker_logs('resources_zookeeper_1', 90, 'Error Path:/consumers/my_consumer/offsets')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'kafka_consumer'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml stop)
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml rm -f)
    end

    task :execute do
      exception = nil
      begin
        %w(before_install install before_script).each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        if !ENV['SKIP_TEST']
          Rake::Task["#{flavor.scope.path}:script"].invoke
        else
          puts 'Skipping tests'.yellow
        end
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
