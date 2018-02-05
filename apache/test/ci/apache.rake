require 'ci/common'

def apache_version
  ENV['FLAVOR_VERSION'] || '2.4.12'
end

def apache_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/apache_#{apache_version}"
end

container_name = 'dd-test-apache'
container_port = 8180

namespace :ci do
  namespace :apache do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('apache')
      sh %(docker create --expose #{container_port} -p #{container_port}:#{container_port} --name #{container_name} httpd:#{apache_version})
      sh %(docker cp #{__dir__}/httpd.conf #{container_name}:/usr/local/apache2/conf/httpd.conf)
      sh %(docker start #{container_name})
      Wait.for 'http://localhost:8180', 15
    end

    task before_script: ['ci:common:before_script'] do
      100.times do
        `curl --silent http://localhost:8180 > /dev/null`
      end
      sleep_for 2
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'apache'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    # sample cleanup task
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
