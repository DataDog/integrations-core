require 'ci/common'

container_name = 'dd-test-php_fpm'

namespace :ci do
  namespace :php_fpm do |flavor|
    task before_install: ['ci:common:before_install']

    task :install do
      Rake::Task['ci:common:install'].invoke('php_fpm')
      sh %(docker create -p 181:80 --name #{container_name} -e NGINX_GENERATE_DEFAULT_VHOST=true million12/nginx-php:php55)
      sh %(docker cp #{__dir__}/fpm-status.conf #{container_name}:/etc/nginx/conf.d/fpm-status.conf)
      sh %(docker start #{container_name})
    end

    task before_script: ['ci:common:before_script'] do
      # Wait for resonse from php ping
      count = 0
      logs = `curl http://localhost:181/ping 2>&1`
      puts 'Waiting for PHP-FPM to come up'
      until count == 20 || logs.include?('pong')
        sleep_for 2
        logs = `curl http://localhost:181/ping 2>&1`
        count += 1
      end
      if logs.include? 'pong'
        puts 'PHP-FPM is up!'
      else
        sh %(docker logs #{container_name} 2>&1)
        raise
      end
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'php_fpm'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f #{container_name})
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
