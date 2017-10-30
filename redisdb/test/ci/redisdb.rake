require 'ci/common'

def redisdb_version
  ENV['FLAVOR_VERSION'] || '2.8.19'
end

def redisdb_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/redisdb_#{redisdb_version}"
end

base_container_name = 'dd-test-redis'
container_port = 16_379
redis_servers = %w(noauth auth slave_healthy slave_unhealthy)

namespace :ci do
  namespace :redisdb do |flavor|
    task before_install: ['ci:common:before_install'] do
      redis_servers.each do |server|
        sh %(docker kill #{base_container_name}-#{server} 2>/dev/null || true)
        sh %(docker rm #{base_container_name}-#{server} 2>/dev/null || true)
        sh %(rm #{__dir__}/#{server}.tmp.conf 2>/dev/null || true)
      end
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('redisdb')

      redis_image = if redisdb_version == '2.4.18'
                      'mtirsel/redis-2.4'
                    else
                      "redis:#{redisdb_version}"
                    end

      %w(noauth auth slave_healthy slave_unhealthy).each do |server|
        p container_port
        container_name = "#{base_container_name}-#{server}"
        sh %(cp -f #{__dir__}/#{server}.conf #{__dir__}/#{server}.tmp.conf)

        if server != 'noauth'
          redis_master_ip = `docker inspect dd-test-redis-noauth | grep '"IPAddress"'`[/([0-9\.]+)/]
          link = "--link #{base_container_name}-noauth:#{server}"
          if server != 'slave_unhealthy'
            sh %(echo "slaveof #{redis_master_ip} 16379" >> #{__dir__}/#{server}.tmp.conf)
          end
        end

        sh %(docker run -v #{__dir__}/#{server}.tmp.conf:/etc/redis.conf #{link} --expose #{container_port} \
             -p #{container_port}:#{container_port} \
             --name #{container_name} -d #{redis_image} redis-server /etc/redis.conf)

        container_port += 10_000
      end
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'redisdb'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      redis_servers.each do |server|
        sh %(docker kill #{base_container_name}-#{server} 2>/dev/null || true)
        sh %(docker rm #{base_container_name}-#{server} 2>/dev/null || true)
        sh %(rm #{__dir__}/#{server}.tmp.conf 2>/dev/null || true)
      end
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
