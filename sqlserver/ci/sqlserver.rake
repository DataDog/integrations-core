require 'ci/common'

def sqlserver_version
  ENV['FLAVOR_VERSION'] || 'latest'
end

container_repo = "microsoft/mssql-server-linux:#{sqlserver_version}"
container_name = 'dd-test-sqlserver'
container_port = 1443
sqlserver_sa_pass = 'dd-ci'

namespace :ci do
  namespace :sqlserver do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('sqlserver/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)

      sh %(docker run -e 'ACCEPT_EULA=Y' -e '#{sqlserver_sa_pass}' -p #{container_port}:#{container_port} --name #{container_name} -d #{container_repo}) unless Gem.win_platform?
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'sqlserver'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      unless Gem.win_platform?
        sh %(docker stop #{container_name} 2>&1 >/dev/null || true 2>&1 >/dev/null)
        sh %(docker rm #{container_name} 2>&1 >/dev/null || true 2>&1 >/dev/null)
      end
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
