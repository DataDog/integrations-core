require 'ci/common'

def twemproxy_version
  ENV['FLAVOR_VERSION'] || '2.4.12'
end

def twemproxy_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/twemproxy_#{twemproxy_version}"
end

namespace :ci do
  namespace :twemproxy do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('twemproxy/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      # sample docker usage
      sh %(docker run --name=redis-A -d -p 6101:6379 redis)
      sh %(docker run --name=redis-B -d -p 6102:6379 redis)
      Wait.for 6101
      Wait.for 6102
      sh %(docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -p 4001:4001 -p 2380:2380 -p 2379:2379 --name etcd quay.io/coreos/etcd:v2.2.0 \
      -name etcd0 \
      -advertise-client-urls http://0.0.0.0:2379,http://0.0.0.0:4001,http://172.17.0.1:2379,http://172.17.0.1:4001 \
      -listen-client-urls http://0.0.0.0:2379,http://0.0.0.0:4001 \
      -initial-advertise-peer-urls http://0.0.0.0:2380 \
      -listen-peer-urls http://0.0.0.0:2380 \
      -initial-cluster-token etcd-cluster-1 \
      -initial-cluster etcd0=http://0.0.0.0:2380 \
      -initial-cluster-state new)
      Wait.for 2379
      sleep_for 5
      # set etcd config
      sh %(curl -L -X PUT http://127.0.0.1:2379/v2/keys/services/redis/01 -d value="172.17.0.1:6101")
      sh %(curl -L -X PUT http://127.0.0.1:2379/v2/keys/services/redis/02 -d value="172.17.0.1:6102")
      sh %(curl -L -X PUT http://127.0.0.1:2379/v2/keys/services/twemproxy/port -d value="6100")
      sh %(curl -L -X PUT http://127.0.0.1:2379/v2/keys/services/twemproxy/host -d value="172.17.0.1")
      # publish the redis host:ip information into etcd
      sh %(docker run --name=twemproxy -d -p 6100:6100 -p 6222:6222 -e ETCD_HOST=172.17.0.1:4001 jgoodall/twemproxy)
      # sh %(docker create -p XXX:YYY --name twemproxy source/twemproxy)
      # sh %(docker start twemproxy)
    end

    task before_script: ['ci:common:before_script'] do
      Wait.for 6100
      Wait.for 6222
      sleep_for 15
      sh %(netstat -ntplu)
      sh %(ifconfig -a)
      sh %(curl -L -X GET http://127.0.0.1:6222)
    end

    task :script, [:mocked] => ['ci:common:script'] do |_, attr|
      ci_home = File.dirname(__FILE__)
      mocked = attr[:mocked] || false
      this_provides = [
        'twemproxy'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides, ci_home, mocked)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker rm -f twemproxy)
      sh %(docker rm -f etcd)
      sh %(docker rm -f redis-A)
      sh %(docker rm -f redis-B)
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
