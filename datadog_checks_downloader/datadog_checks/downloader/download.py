# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import collections
import glob
import logging
import logging.config
import os
import pathlib
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from in_toto import verifylib
from in_toto.exceptions import LinkNotFoundError
from in_toto.models.metadata import Metablock
from packaging.version import parse as parse_version
from securesystemslib import interface
from tuf.ngclient import Updater

from .exceptions import (
    DuplicatePackage,
    InconsistentSimpleIndex,
    IncorrectRootLayoutType,
    MissingVersions,
    NoInTotoLinkMetadataFound,
    NoInTotoRootLayoutPublicKeysFound,
    NoSuchDatadogPackage,
    NoSuchDatadogPackageVersion,
    PythonVersionMismatch,
    RevokedDeveloperOrMachine,
    TargetNotFoundError,
)
from .parameters import substitute

# After we import everything we need, shut off all existing loggers.
logging.config.dictConfig({'disable_existing_loggers': True, 'version': 1})


# CONSTANTS.
here = os.path.abspath(os.path.dirname(__file__))
REPOSITORIES_DIR = os.path.join(here, 'data')
# abspath = os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR)
REPOSITORY_DIR = 'repo'
REPOSITORY_URL_PREFIX = 'https://dd-integrations-core-wheels-build-stable.datadoghq.com'
# Where to find our in-toto root layout.
IN_TOTO_METADATA_DIR = 'in-toto-metadata'
ROOT_LAYOUTS = {'core': '5.core.root.layout', 'extras': '1.extras.root.layout'}
DEFAULT_ROOT_LAYOUT_TYPE = 'core'


# Global variables.
logger = logging.getLogger(__name__)


class TUFDownloader:
    def __init__(
        self,
        repository_url_prefix=REPOSITORY_URL_PREFIX,
        root_layout_type=DEFAULT_ROOT_LAYOUT_TYPE,
        verbose=0,
        disable_verification=False,
    ):
        # 0 => 60 (effectively /dev/null)
        # 1 => 50 (CRITICAL)
        # 2 => 40 (ERROR)
        # 3 => 30 (WARNING)
        # 4 => 20 (INFO)
        # 5 => 10 (DEBUG)
        remainder = min(verbose, 5) % 6
        level = (6 - remainder) * 10
        assert level in range(10, 70, 10), level
        logging.basicConfig(format='%(levelname)-8s: %(message)s', level=level)

        self.__root_layout_type = root_layout_type
        self.__root_layout = ROOT_LAYOUTS[self.__root_layout_type]

        self.__disable_verification = disable_verification

        if self.__disable_verification:
            logger.warning(
                'Running with TUF and in-toto verification disabled. Integrity is only protected with TLS (HTTPS).'
            )

        # NOTE: The directory where the targets for *this* repository is
        # cached. We hard-code this keep this to a subdirectory dedicated to
        # this repository.
        self.__targets_dir = os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR, 'targets')

        # NOTE: Build a TUF updater which stores metadata in (1) the given
        # directory, and (2) uses the following mirror configuration,
        # respectively.
        # NOTE: This updater will store files under:
        # os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR)
        self.__updater = Updater(
            metadata_dir=os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR, 'metadata'),
            metadata_base_url=f'{repository_url_prefix}/metadata.staged/',
            target_base_url=f'{repository_url_prefix}/targets/',
            target_dir=self.__targets_dir,
        )

        # Increase requests timeout.
        # There's no officially supported way to do this without either writing our own
        # fetcher from scratch or relying on internals. We're choosing the latter for now.
        # - https://github.com/theupdateframework/python-tuf/blob/v2.0.0/tuf/ngclient/updater.py#L99
        # - https://github.com/theupdateframework/python-tuf/blob/v2.0.0/tuf/ngclient/_internal/requests_fetcher.py#L49
        self.__updater._fetcher.socket_timeout = 60

        # NOTE: Update to the latest top-level role metadata only ONCE, so that
        # we use the same consistent snapshot to download targets.
        self.__updater.refresh()

    def __compute_target_paths(self, target_relpath):
        # The path used to query TUF needs to be a path-relative-URL string
        # (https://url.spec.whatwg.org/#path-relative-url-string), which means the path
        # separator *must* be `/` and only `/`.
        # This is a defensive measure to make things work even if the provided `target_relpath`
        # is a platform-specific filesystem path.
        tuf_target_path = pathlib.PurePath(target_relpath).as_posix()
        target_abspath = os.path.join(self.__targets_dir, tuf_target_path)

        return tuf_target_path, target_abspath

    def _download_without_tuf_in_toto(self, target_relpath):
        assert isinstance(self.__updater._target_base_url, str), self.__updater._target_base_url

        tuf_target_path, target_abspath = self.__compute_target_paths(target_relpath)

        # reproducing how the "self.__updater.download_target" method computes the URL
        target_base_url = self.__updater._target_base_url
        full_url = target_base_url + ('/' if not target_base_url.endswith('/') else '') + tuf_target_path

        try:
            with urllib.request.urlopen(full_url) as resp:
                os.makedirs(os.path.dirname(target_abspath), exist_ok=True)
                with open(target_abspath, 'wb') as dest:
                    dest.write(resp.read())
        except urllib.error.HTTPError as err:
            logger.error('GET %s: %s', full_url, err)
            raise

        return target_abspath

    def _download_with_tuf(self, target_relpath):
        tuf_target_path, target_abspath = self.__compute_target_paths(target_relpath)

        target = self.__updater.get_targetinfo(tuf_target_path)
        if target is None:
            raise TargetNotFoundError(f'Target at {tuf_target_path} not found')

        local_relpath = self.__updater.find_cached_target(target, target_abspath)

        # Either the target has not been updated...
        if local_relpath:
            logger.debug('%s has not been updated', tuf_target_path)
        # or, it has been updated, in which case we download the new version
        else:
            os.makedirs(os.path.dirname(target_abspath), exist_ok=True)
            self.__updater.download_target(target, target_abspath)

        logger.info('TUF verified %s', tuf_target_path)

        return target_abspath, target

    def __download_in_toto_root_layout(self):
        # NOTE: We expect the root layout to be signed with *offline* keys.
        # NOTE: We effectively tie every version of this downloader to its
        # expected version of the root layout. This is so that, for example, we
        # can introduce new parameters w/o breaking old downloaders that don't
        # know how to substitute them.
        target_relpath = f'{IN_TOTO_METADATA_DIR}/{self.__root_layout}'
        return self._download_with_tuf(target_relpath)

    def __download_custom(self, target, extension):
        # A set to collect where in-toto pubkeys / links live.
        target_abspaths = set()

        custom = target.custom

        root_layout_type = custom.get('root-layout-type', DEFAULT_ROOT_LAYOUT_TYPE)
        if root_layout_type != self.__root_layout_type:
            raise IncorrectRootLayoutType(root_layout_type, self.__root_layout_type)

        in_toto_metadata = custom.get('in-toto', [])

        for target_relpath in in_toto_metadata:
            # Download in-toto *link* metadata files using TUF,
            # which, among other things, prevents mix-and-match
            # attacks by MitM attackers, and rollback attacks even
            # by attackers who control the repository:
            # https://www.usenix.org/conference/atc17/technical-sessions/presentation/kuppusamy
            # NOTE: Avoid recursively downloading in-toto metadata
            # for in-toto metadata themselves, and so on ad
            # infinitum.
            if target_relpath.endswith(extension):
                target_abspath, _ = self._download_with_tuf(target_relpath)

                # Add this file to the growing collection of where
                # in-toto pubkeys / links live.
                target_abspaths.add(target_abspath)

        # Return list of where in-toto metadata files live.
        return target_abspaths

    def __download_in_toto_layout_pubkeys(self, target, target_relpath):
        """
        NOTE: We assume that all the public keys needed to verify any in-toto
        root layout, or sublayout, metadata file has been directly signed by
        the top-level TUF targets role using *OFFLINE* keys. This is a
        reasonable assumption, as TUF does not offer meaningful security
        guarantees if _ALL_ targets were signed using _online_ keys.
        """

        pubkey_abspaths = self.__download_custom(target, '.pub')
        if not len(pubkey_abspaths):
            raise NoInTotoRootLayoutPublicKeysFound(target_relpath)
        else:
            return pubkey_abspaths

    def __download_in_toto_links(self, target, target_relpath):
        link_abspaths = self.__download_custom(target, '.link')
        if not len(link_abspaths):
            raise NoInTotoLinkMetadataFound(target_relpath)
        else:
            return link_abspaths

    def __load_root_layout(self, target_relpath):
        root_layout = Metablock.load(self.__root_layout)
        root_layout_pubkeys = glob.glob('*.pub')
        root_layout_pubkeys = interface.import_publickeys_from_file(root_layout_pubkeys)
        # Parameter substitution.
        root_layout_params = substitute(target_relpath)
        return root_layout, root_layout_pubkeys, root_layout_params

    def __handle_in_toto_verification_exception(self, target_relpath, e):
        logger.exception('in-toto failed to verify %s', target_relpath)

        if isinstance(e, LinkNotFoundError) and str(e) == RevokedDeveloperOrMachine.MSG:
            raise RevokedDeveloperOrMachine(target_relpath, self.__root_layout)
        else:
            raise e

    def __in_toto_verify(self, inspection_packet, target_relpath):
        # Make a temporary directory in a parent directory we control.
        tempdir = tempfile.mkdtemp(dir=REPOSITORIES_DIR)

        try:
            # Copy files over into temp dir.
            for abs_path in inspection_packet:
                shutil.copy(abs_path, tempdir)

            # Switch to the temp dir.
            os.chdir(tempdir)

            # Load the root layout and public keys in this temp dir.
            root_layout, root_layout_pubkeys, root_layout_params = self.__load_root_layout(target_relpath)

            verifylib.in_toto_verify(root_layout, root_layout_pubkeys, substitution_parameters=root_layout_params)
        except Exception as e:
            self.__handle_in_toto_verification_exception(target_relpath, e)
        else:
            logger.info('in-toto verified %s', target_relpath)
        finally:
            # Switch back to a parent directory we control, so that we can
            # safely delete temp dir.
            os.chdir(REPOSITORIES_DIR)
            # Delete temp dir.
            shutil.rmtree(tempdir)

    def __download_and_verify_in_toto_metadata(self, target_relpath, target_abspath, target):
        # First, get our in-toto root layout.
        root_layout_abspath, root_layout_target = self.__download_in_toto_root_layout()
        inspection_packet = {target_abspath, root_layout_abspath}

        # Second, get the public keys for the root layout.
        pubkey_abspaths = self.__download_in_toto_layout_pubkeys(root_layout_target, target_relpath)

        # Third, get the in-toto links for the target of interest.
        link_abspaths = self.__download_in_toto_links(target, target_relpath)

        # Everything we need for in-toto inspection to work: the wheel,
        # the in-toto root layout, in-toto links, and public keys to
        # verify the in-toto layout.
        inspection_packet |= pubkey_abspaths | link_abspaths
        self.__in_toto_verify(inspection_packet, target_relpath)

    def _download_with_tuf_in_toto(self, target_relpath):
        target_abspath, target = self._download_with_tuf(target_relpath)

        # Next, we use in-toto to verify the supply chain of the target.
        # NOTE: We use a flag to avoid recursively downloading in-toto
        # metadata for in-toto metadata themselves, and so on ad infinitum.
        # All other files, presumably packages, should also be
        # inspected.
        try:
            self.__download_and_verify_in_toto_metadata(target_relpath, target_abspath, target)
        except Exception:
            os.remove(target_abspath)
            raise
        else:
            return target_abspath

    def download(self, target_relpath):
        """
        Returns:
            If download over TUF and in-toto is successful, this function will
            return the complete filepath to the desired target.
        """
        if self.__disable_verification:
            target_abspath = self._download_without_tuf_in_toto(target_relpath)
        else:
            target_abspath = self._download_with_tuf_in_toto(target_relpath)
        # Always return the posix version of the path for consistency across platforms
        return pathlib.Path(target_abspath).as_posix()

    def __get_versions(self, standard_distribution_name):
        index_relpath = 'simple/{}/index.html'.format(standard_distribution_name)
        # https://www.python.org/dev/peps/pep-0491/#escaping-and-unicode
        wheel_distribution_name = re.sub('[^\\w\\d.]+', '_', standard_distribution_name, re.UNICODE)  # noqa: B034
        pattern = "<a href='(" + wheel_distribution_name + "-(.*?)-(.*?)-none-any\\.whl)'>(.*?)</a><br />"
        # version: {python_tag: href}
        wheels = collections.defaultdict(dict)

        if self.__disable_verification:
            index_abspath = self._download_without_tuf_in_toto(index_relpath)
        else:
            try:
                # NOTE: We do not perform in-toto inspection for simple indices; only for wheels.
                index_abspath, _ = self._download_with_tuf(index_relpath)
            except TargetNotFoundError:
                raise NoSuchDatadogPackage(standard_distribution_name)

        with open(index_abspath) as simple_index:
            for line in simple_index:
                match = re.match(pattern, line)

                if match:
                    href, version, python_tag, text = match.groups()

                    if href != text:
                        raise InconsistentSimpleIndex(href, text)
                    else:
                        python_tags = wheels[version]
                        if python_tag in python_tags:
                            raise DuplicatePackage(standard_distribution_name, version, python_tag)
                        python_tags[python_tag] = href

        return wheels

    def get_wheel_relpath(self, standard_distribution_name, version=None, ignore_python_version=False):
        """
        Returns:
            If download over TUF is successful, this function will return the
            latest known version of the Datadog integration.
        """
        wheels = self.__get_versions(standard_distribution_name)

        if not wheels:
            raise MissingVersions(standard_distribution_name)

        if not version:
            # Go through all wheels and remove alphas, betas and rcs and pick the latest version
            # https://packaging.pypa.io/en/latest/version.html
            version = str(max(parse_version(v) for v in wheels.keys() if not parse_version(v).is_prerelease))

        python_tags = wheels[version]
        if not python_tags:
            raise NoSuchDatadogPackageVersion(standard_distribution_name, version)

        # First, try finding the pure Python wheel for this version.
        this_python = 'py{}'.format(sys.version_info[0])
        href = python_tags.get(this_python)

        # Otherwise, try finding the universal Python wheel for this version.
        if not href:
            href = python_tags.get('py2.py3')

        # Otherwise, fuhgedaboutit.
        if not href:
            if ignore_python_version:
                href = list(python_tags.values())[0]
            else:
                raise PythonVersionMismatch(standard_distribution_name, version, this_python, python_tags)

        return 'simple/{}/{}'.format(standard_distribution_name, href)
