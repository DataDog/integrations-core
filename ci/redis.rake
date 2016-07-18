require 'ci/common'

def redis_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def redis_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/redis_#{redis_version}"
end

namespace :ci do
  namespace :redis do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('redis/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      # sample docker usage
      sh %(docker run -p 6379:6379  --name redis redis:#{redis_version})
    end

    task before_script: ['ci:common:before_script']

    task :script, [:mocked] => ['ci:common:script'] do |_, attr|
      ci_home = File.dirname(__FILE__)
      mocked = attr[:mocked] || false
      this_provides = [
        'redis'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides, ci_home, mocked)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']
    # sample cleanup task
    # task cleanup: ['ci:common:cleanup'] do 
    #   sh %(docker stop redis)
    #   sh %(docker rm redis)
    # end

    task :execute, :mocked do |_, attr|
      mocked = attr[:mocked] || false
      exception = nil
      begin
        if not mocked
          %w(before_install install before_script).each do |u|
            Rake::Task["#{flavor.scope.path}:#{u}"].invoke
          end
        end
        Rake::Task["#{flavor.scope.path}:script"].invoke(mocked)
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
