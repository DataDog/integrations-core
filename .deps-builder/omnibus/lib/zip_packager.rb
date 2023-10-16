module Omnibus
  module Packager
    # Monkey-patch the method that returns available packagers to return always the one we want
    class << self
      def for_current_system
        [Zipper]
      end
    end

    # A custom packager that puts stuff from the build_dir into a gzipped tarball.
    class Zipper < Packager::Base
      id :zipper

      build do
        Dir.chdir project.install_dir  do
          shellout! "tar -czvf #{File.join(Config.package_dir, package_name)} #{targets}"
        end
      end

      def package_name
        "#{project.package_name}-#{project.build_version}.tar.gz"
      end

      def targets
        @explicit_targets&.join(' ')  || '.'
      end

      # Add a target to the archive, relative to the project's install_dir
      def target(val)
        @explicit_targets ||= []
        @explicit_targets.push(val)
      end
      expose :target
    end
  end
end

