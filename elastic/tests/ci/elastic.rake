require 'ci/common'

def elastic_version
  ENV['FLAVOR_VERSION'] || '1.3.9'
end

def elastic_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/elastic_#{elastic_version}"
end

container_name = 'dd-test-elastic'
container_port1 = 9200
container_port2 = 9300

namespace :ci do
  namespace :elastic do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('elastic')
      docker_cmd = 'elasticsearch -Des.node.name="batman" '
      if ['0.90.13', '1.0.3', '1.1.2', '1.2.4'].any? { |v| v == elastic_version }
        docker_image = 'datadog/docker-library:elasticsearch_' + elastic_version.split('.')[0..1].join('_')
        docker_cmd += ' -f' if elastic_version == '0.90.13'
      else
        docker_image = "elasticsearch:#{elastic_version}"
      end
      container_ports =  "-p #{container_port1}:#{container_port1} -p #{container_port2}:#{container_port2}"
      sh %(docker run -d #{container_ports} --name #{container_name} #{docker_image} #{docker_cmd})
      ENV['DD_ELASTIC_LOCAL_HOSTNAME'] = if elastic_version[0].to_i < 2
                                           `docker inspect dd-test-elastic | grep Id`[/([0-9a-f\.]{2,})/][0..11]
                                         else
                                           `docker inspect dd-test-elastic | grep IPAddress`[/([0-9\.]+)/]
                                         end
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for 'http://localhost:9200', 20
      # Create an index in ES
      http = Net::HTTP.new('localhost', 9200)
      http.send_request('PUT', '/datadog/')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'elastic'
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
