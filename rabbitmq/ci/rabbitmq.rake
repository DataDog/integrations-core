require 'ci/common'

def rabbitmq_version
  ENV['FLAVOR_VERSION'] || '3.5.0'
end

def rabbitmq_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/rabbitmq_#{rabbitmq_version}"
end

container_name = 'dd-test-rabbitmq'
container_port1 = 5672
container_port2 = 15_672

namespace :ci do
  namespace :rabbitmq do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('rabbitmq')
      sh %(docker run -d --name #{container_name} \
           -p #{container_port1}:#{container_port1} \
           -p #{container_port2}:#{container_port2} \
           rabbitmq:#{rabbitmq_version}-management)
    end

    task before_script: ['ci:common:before_script'] do
      # Wait for RabbitMQ to come up
      count = 0
      logs = `docker logs #{container_name} 2>&1`
      puts 'Waiting for RabbitMQ to come up'
      until count == 20 || logs.include?('Server startup complete')
        sleep_for 2
        logs = `docker logs #{container_name} 2>&1`
        count += 1
      end
      if logs.include?('Server startup complete')
        puts 'RabbitMQ is up!'
      else
        sh %(docker logs #{container_name} 2>&1)
        raise 'RabbitMQ failed to come up'
      end

      %w(test1 test5 tralala).each do |q|
        sh %(curl localhost:15672/cli/rabbitmqadmin | python - declare queue name=#{q})
        sh %(curl localhost:15672/cli/rabbitmqadmin | python - publish exchange=amq.default routing_key=#{q} payload="hello, world")
      end
      sh %(curl localhost:15672/cli/rabbitmqadmin | python - list queues)

      # leave time for rabbitmq to update the management information
      sleep_for 2
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'rabbitmq'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
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
