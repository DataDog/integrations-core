require 'ci/common'

def consul_version
  ENV['FLAVOR_VERSION'] || '0.7.2'
end

def consul_config
  "server-#{consul_version}.json"
end

def consul_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/consul_#{consul_version}"
end

container_name_1 = 'dd-test-consul-1'
container_name_2 = 'dd-test-consul-2'
container_name_3 = 'dd-test-consul-3'

namespace :ci do
  namespace :consul do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker stop dd-test-consul-1 dd-test-consul-2 dd-test-consul-3 2>/dev/null || true)
      sh %(docker rm  dd-test-consul-1 dd-test-consul-2 dd-test-consul-3 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('consul')
      # sample docker usage
      sh %( docker run -d --expose 8301 --expose 8500 -p 8500:8500 --name #{container_name_1} \
            --volume #{__dir__}/#{consul_config}:/consul/config/server.json:ro \
            consul:#{consul_version} agent -dev -bind=0.0.0.0 -client=0.0.0.0 )
      Wait.for 8500
      wait_on_docker_logs(container_name_1, 30, 'agent: Node info in sync', "agent: Synced service 'consul'", 'agent: Synced node info')

      consul_first_ip = `docker inspect #{container_name_1} | grep '"IPAddress"'`[/([0-9\.]+)/]
      sh %( docker run -d --expose 8301 --name #{container_name_2} --volume #{__dir__}/#{consul_config}:/consul/config/server.json:ro \
            consul:#{consul_version} agent -dev -join=#{consul_first_ip} -bind=0.0.0.0 )
      wait_on_docker_logs(container_name_2, 30, 'agent: Node info in sync', "agent: Synced service 'consul'", 'agent: Synced node info')

      sh %( docker run -d --expose 8301 --name #{container_name_3} --volume #{__dir__}/#{consul_config}:/consul/config/server.json:ro \
            consul:#{consul_version} agent -dev -join=#{consul_first_ip} -bind=0.0.0.0)
      wait_on_docker_logs(container_name_3, 30, 'agent: Node info in sync', "agent: Synced service 'consul'", 'agent: Synced node info')
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'consul'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker stop dd-test-consul-1 dd-test-consul-2 dd-test-consul-3 2>/dev/null || true)
      sh %(docker rm  dd-test-consul-1 dd-test-consul-2 dd-test-consul-3 2>/dev/null || true)
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
