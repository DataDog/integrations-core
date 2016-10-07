require 'ci/common'

def supervisord_version
  ENV['FLAVOR_VERSION'] || '3.3.0'
end

def supervisord_rootdir
  "#{ENV['INTEGRATIONS_DIR']}/supervisord_#{supervisord_version}"
end

namespace :ci do
  namespace :supervisord do |flavor|
    task before_install: ['ci:common:before_install'] do
      unless Dir.exist? File.expand_path(supervisord_rootdir)
        sh %(pip install supervisor==#{supervisord_version} --ignore-installed\
             --install-option="--prefix=#{supervisord_rootdir}")
      end
    end

    task install: ['ci:common:install'] do
      use_venv = in_venv
      install_requirements('supervisord/requirements.txt',
                           "--cache-dir #{ENV['PIP_CACHE']}",
                           "#{ENV['VOLATILE_DIR']}/ci.log", use_venv)
    end

    task before_script: ['ci:common:before_script'] do
      sh %(mkdir -p $VOLATILE_DIR/supervisor)
      sh %(cp $TRAVIS_BUILD_DIR/supervisord/ci/resources/supervisord.conf\
           $VOLATILE_DIR/supervisor/)
      sh %(sed -i -- 's/VOLATILE_DIR/#{ENV['VOLATILE_DIR'].gsub '/', '\/'}/g'\
         $VOLATILE_DIR/supervisor/supervisord.conf)

      3.times do |i|
        sh %(cp $TRAVIS_BUILD_DIR/supervisord/ci/resources/program_#{i}.sh\
             $VOLATILE_DIR/supervisor/)
      end
      sh %(chmod a+x $VOLATILE_DIR/supervisor/program_*.sh)

      sh %(#{supervisord_rootdir}/bin/supervisord\
           -c $VOLATILE_DIR/supervisor/supervisord.conf)
      3.times { |i| Wait.for "#{ENV['VOLATILE_DIR']}/supervisor/started_#{i}" }
      # And we still have to sleep a little, because sometimes supervisor
      # doesn't immediately realize that its processes are running
      sleep_for 1
    end

    task script: ['ci:common:script'] do
      this_provides = [
        'supervisord'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(kill `cat $VOLATILE_DIR/supervisor/supervisord.pid`)
      sh %(rm -rf $VOLATILE_DIR/supervisor)
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
