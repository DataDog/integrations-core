require 'ci/common'

def statsd_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def statsd_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/statsd_#{statsd_version}"
end

namespace :ci do
  namespace :statsd do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker stop dd-test-statsd || true)
      sh %(docker rm dd-test-statsd || true)
    end

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('statsd/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(docker run -p 8125:8125/udp -p 8126:8126 -d --name dd-test-statsd jolexa/docker-statsd)
      sleep 5
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'statsd'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker stop dd-test-statsd || true)
      sh %(docker rm dd-test-statsd || true)
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
