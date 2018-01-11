require 'ci/common'

def twemproxy_version
  ENV['FLAVOR_VERSION'] || '2.4.12'
end

def twemproxy_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/twemproxy_#{twemproxy_version}"
end

def docker_addr
  ENV['DOCKER_ADDR'] || '172.17.0.1'
end

namespace :ci do
  namespace :twemproxy do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('twemproxy')
      # sample docker usage
      sh %(#{ENV['SDK_HOME']}/twemproxy/test/ci/start-docker.sh #{docker_addr})
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for 6100
      Wait.for 6222
      sleep_for 15
      sh %(curl -L -X GET http://127.0.0.1:6222 || echo)
    end

    task :script, [:mocked] => ['ci:common:script'] do |_, attr|
      mocked = attr[:mocked] || false
      this_provides = [
        'twemproxy'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides, mocked)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(#{ENV['SDK_HOME']}/twemproxy/test/ci/stop-docker.sh #{docker_addr})
    end
    # sample cleanup task
    # task cleanup: ['ci:common:cleanup'] do
    #   sh %(docker stop twemproxy)
    #   sh %(docker rm twemproxy)
    # end

    task :execute, :mocked do |_, attr|
      mocked = attr[:mocked] || false
      exception = nil
      begin
        unless mocked
          %w(before_install install before_script).each do |u|
            Rake::Task["#{flavor.scope.path}:#{u}"].invoke
          end
        end
        if !ENV['SKIP_TEST']
          Rake::Task["#{flavor.scope.path}:script"].invoke(mocked)
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
