require 'ci/common'

def gunicorn_version
  ENV['FLAVOR_VERSION'] || '19.6.0'
end

def gunicorn_rootdir
  volatile_dir = ENV['VOLATILE_DIR'] || "#{ENV['SDK_HOME']}/embedded"
  "#{volatile_dir}/supervisord"
end

namespace :ci do
  namespace :gunicorn do |flavor|
    task before_install: ['ci:common:before_install'] do
      sh %(ps ax | grep dd-test-gunicorn | grep -v grep | grep -v rake | awk '{ print $1 }' | xargs kill -9 || true)
      rm_rf gunicorn_rootdir
    end

    task :install do
      Rake::Task['ci:common:install'].invoke('gunicorn')
      section('GUNICORN_INSTALL')
      `mkdir -p #{gunicorn_rootdir}/venv`
      `mkdir -p #{gunicorn_rootdir}/app`
      `wget -q -O #{gunicorn_rootdir}/venv/virtualenv.py https://raw.github.com/pypa/virtualenv/1.11.6/virtualenv.py`
      `python #{gunicorn_rootdir}/venv/virtualenv.py  --no-site-packages --no-pip --no-setuptools #{gunicorn_rootdir}/venv/`
      `wget -q -O #{gunicorn_rootdir}/venv/ez_setup.py https://bootstrap.pypa.io/ez_setup.py`
      `#{gunicorn_rootdir}/venv/bin/python #{gunicorn_rootdir}/venv/ez_setup.py`
      `wget -q -O #{gunicorn_rootdir}/venv/get-pip.py https://bootstrap.pypa.io/get-pip.py`
      `#{gunicorn_rootdir}/venv/bin/python #{gunicorn_rootdir}/venv/get-pip.py`
      `#{gunicorn_rootdir}/venv/bin/pip install gunicorn==#{gunicorn_version} gevent setproctitle`
      `#{gunicorn_rootdir}/venv/bin/pip install setproctitle`
      cp "#{ENV['SDK_HOME']}/gunicorn/ci/conf.py", "#{gunicorn_rootdir}/conf.py"
      open("#{gunicorn_rootdir}/conf.py", 'a') do |f|
        f.puts "chdir = \"#{gunicorn_rootdir}/app\""
      end
      cp "#{ENV['SDK_HOME']}/gunicorn/ci/app.py", "#{gunicorn_rootdir}/app/app.py"
      Process.spawn "#{gunicorn_rootdir}/venv/bin/gunicorn --config=#{gunicorn_rootdir}/conf.py --name=dd-test-gunicorn app:app"
    end

    task before_script: ['ci:common:before_script']

    task script: ['ci:common:script'] do
      this_provides = [
        'gunicorn'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup'] do
      sh %(ps ax | grep dd-test-gunicorn | grep -v grep | grep -v rake | awk '{ print $1 }' | xargs kill -9 || true)
      rm_rf gunicorn_rootdir
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
