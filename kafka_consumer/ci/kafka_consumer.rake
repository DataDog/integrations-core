require 'ci/common'

def kafka_consumer_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def kafka_consumer_options
  ENV['FLAVOR_OPTIONS'] || 'zookeeper'
end

def kafka_topics
  ENV['KAFKA_TOPICS'] || 'marvel:2:1,dc:2:1'
end

def zookeeper_version
  ENV['ZOOKEEPER_VERSION'] || '3.4.9'
end

kafka_legacy = '0.8.2.0'

namespace :ci do
  namespace :kafka_consumer do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('kafka_consumer')
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 KAFKA_OFFSETS_STORAGE=#{kafka_consumer_options} KAFKA_CREATE_TOPICS=#{kafka_topics} \
           ZOOKEEPER_VERSION=#{zookeeper_version} JMX_PORT=9999 KAFKA_HEAP_OPTS="-Xmx256M -Xms128M" \
           KAFKA_ADVERTISED_HOST_NAME="172.17.0.1" KAFKA_ZOOKEEPER_CONNECT="zookeeper:2181" \
           docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml up -d)
      Wait.for 2181
      Wait.for 9092
      wait_on_docker_logs('resources_kafka_1', 20, ' started (kafka.server.KafkaServer)')
      wait_on_docker_logs('resources_zookeeper_1', 20, 'NoNode for /brokers')
      if Gem::Version.new(kafka_consumer_version) > Gem::Version.new(kafka_legacy)
        wait_on_docker_logs('resources_kafka_1', 20, 'Created topic "marvel"')
        wait_on_docker_logs('resources_kafka_1', 20, 'Created topic "dc"')
      end

      sh %(EXTERNAL_PORT=9091 EXTERNAL_JMX_PORT=9998 CONSUMER_OFFSET_STORAGE=#{kafka_consumer_options} KAFKA_TOPICS=#{kafka_topics} \
           ZOOKEEPER_VERSION=#{zookeeper_version} \
           docker-compose -f #{ENV['TRAVIS_BUILD_DIR']}/kafka/ci/resources/docker-compose-single-broker.yml scale kafka=2)
      wait_on_docker_logs('resources_kafka_2', 20, ' started (kafka.server.KafkaServer)')
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
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 docker-compose -f \
           #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml stop)
      sh %(EXTERNAL_PORT=9092 EXTERNAL_JMX_PORT=9999 docker-compose -f \
           #{ENV['TRAVIS_BUILD_DIR']}/kafka_consumer/ci/resources/docker-compose-single-broker.yml rm -f)
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
