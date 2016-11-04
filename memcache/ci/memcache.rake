require 'ci/common'

def memcache_version
  ENV['FLAVOR_VERSION'] || '1.4.22'
end

def memcache_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/memcache_#{memcache_version}"
end

container_name = 'dd-test-memcache'
container_port = 11212

namespace :ci do
  namespace :memcache do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
    end

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('memcache/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
      sh %(docker run -d --name #{container_name} -p #{container_port}:11211 memcached:#{memcache_version})

      memcache_response = `#{__dir__}/mc_conn_tester.pl -s localhost -p #{container_port} -c 1 --timeout 1`
      count = 0
      until count == 20 || memcache_response.include?("loop: (timeout: 1) (elapsed:")
        sleep_for 2
        memcache_response = `#{__dir__}/mc_conn_tester.pl -s localhost -p #{container_port} -c 1 --timeout 1`
        count += 1
      end
      if memcache_response.include?("loop: (timeout: 1) (elapsed:")
        p "memcache is up!"
      else
        print "Raw Memcache Stats for debugging:"
        sh %(mkdir -p embedded)
        sh %(curl -L https://cpanmin.us/ -o embedded/cpanm && chmod +x embedded/cpanm)
        sh %(./embedded/cpanm --local-lib=~/perl5 local::lib && eval $(perl -I ~/perl5/lib/perl5/ -Mlocal::lib))
        sh %(./embedded/cpanm --local-lib=~/perl5 Cache::Memcached)
        sh %(perl -I ~/perl5/lib/perl5/ -MCache::Memcached -MData::Dumper=Dumper -le  'print Dumper(Cache::Memcached->new(  servers => ["localhost:11212"])->stats);')
        raise "memcache failed to come up!"
      end
    end

    task before_script: ['ci:common:before_script'] do
      # If you need to debug this, uncomment this line. We don't want to run this every time.
      # print "Raw Memcache Stats for debugging:"
      # sh %(mkdir -p embedded)
      # sh %(curl -L https://cpanmin.us/ -o embedded/cpanm && chmod +x embedded/cpanm)
      # sh %(./embedded/cpanm --local-lib=~/perl5 local::lib && eval $(perl -I ~/perl5/lib/perl5/ -Mlocal::lib))
      # sh %(./embedded/cpanm --local-lib=~/perl5 Cache::Memcached)
      # sh %(perl -I ~/perl5/lib/perl5/ -MCache::Memcached -MData::Dumper=Dumper -le  'print Dumper(Cache::Memcached->new(  servers => ["localhost:11212"])->stats);')
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'memcache'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(docker kill #{container_name} 2>/dev/null || true)
      sh %(docker rm #{container_name} 2>/dev/null || true)
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
