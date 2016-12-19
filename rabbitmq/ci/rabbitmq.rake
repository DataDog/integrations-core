require 'ci/common'

def rabbitmq_version
  ENV['FLAVOR_VERSION'] || '3.5.0'
end

def rabbitmq_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/rabbitmq_#{rabbitmq_version}"
end

namespace :ci do
  namespace :rabbitmq do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('rabbitmq/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      run_shell_script %(rabbitmq/ci/start-docker.sh)
    end

    task before_script: ['ci:common:before_script'] do
      run_shell_script %(mkdir -p tmp)
      run_shell_script %(wget localhost:15672/cli/rabbitmqadmin -O tmp/rabbitmqadmin)
      %w(test1 test5 tralala).each do |q|
        run_shell_script %(python tmp/rabbitmqadmin declare queue name=#{q})
        run_shell_script %(python tmp/rabbitmqadmin publish exchange=amq.default routing_key=#{q} payload="hello, world")
      end
      run_shell_script %(python tmp/rabbitmqadmin list queues)
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'rabbitmq'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']
    # sample cleanup task
    task cleanup: ['ci:common:cleanup'] do
      run_shell_script %(stop-docker dd-test-rabbitmq)
      run_shell_script %(rm -rf tmp/rabbitmqadmin)
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
