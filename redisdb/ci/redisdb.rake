require 'ci/common'

def redis_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

def redis_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/redis_#{redis_version}"
end

namespace :ci do
  namespace :redisdb do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('redisdb/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      # sample docker usage
      sh %(docker run -d -p 16379:6379 --name redis-master redis:#{redis_version})
      sh %(docker run -d -p 26379:6379 --name redis-auth --link redis-master redis:#{redis_version} redis-server --requirepass datadog-is-devops-best-friend --slaveof redis-master 6379)
      sh %(docker run -d -p 36379:6379 --name redis-slave-healthy --link redis-master redis:#{redis_version} redis-server --slaveof redis-master 6379)
      sh %(docker run -d -p 46379:6379 --name redis-slave-unhealthy --link redis-master redis:#{redis_version} redis-server --slaveof redis-master 55555)

    end

    task before_script: ['ci:common:before_script']

    task :script => ['ci:common:script'] do |_, attr|
      ci_home = File.dirname(__FILE__)
      this_provides = [
        'redisdb'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides, ci_home)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f redis-master redis-auth redis-slave-healthy redis-slave-unhealthy)
    end

    task :execute, :mocked do |_, attr|
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
