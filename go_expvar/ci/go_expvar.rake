require 'ci/common'

def go_expvar_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def go_expvar_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/go_expvar_#{go_expvar_version}"
end

namespace :ci do
  namespace :go_expvar do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('go_expvar')
      sh %(docker build -t datadog-test-expvar #{ENV['TRAVIS_BUILD_DIR']}/go_expvar/ci/)
      sh %(docker run -dt --name datadog-test-expvar -p 8079:8079 datadog-test-expvar)
      sleep_for 5
      sh %(while ! curl -s http://localhost:8079?user=123456; do echo "Waiting for application"; sleep 5; done)
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'go_expvar'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f datadog-test-expvar)
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
