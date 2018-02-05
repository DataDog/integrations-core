require 'ci/common'

def squid_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def squid_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/squid_#{squid_version}"
end

namespace :ci do
  namespace :squid do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('squid')
      # sample docker usage
      sh %(docker run -d -p 3128:3128 --name squid datadog/squid:#{squid_version})
      sh %(docker exec squid sed -i -e s/http_access\\ deny\\ manager/\\ #http_access\\ deny\\ manager/ /etc/squid/squid.conf)
      sh %(docker restart squid)
    end

    task before_script: ['ci:common:before_script'] do
      wait_on_docker_logs('squid', 10, 'Accepting HTTP Socket connections')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'squid'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker stop squid)
      sh %(docker rm squid)
    end

    task :execute do
      exception = nil
      begin
        %w[before_install install before_script].each do |u|
          Rake::Task["#{flavor.scope.path}:#{u}"].invoke
        end
        if !ENV['SKIP_TEST']
          Rake::Task["#{flavor.scope.path}:script"].invoke
        else
          puts 'Skipping tests'.yellow
        end
        Rake::Task["#{flavor.scope.path}:before_cache"].invoke
      rescue StandardError => e
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
