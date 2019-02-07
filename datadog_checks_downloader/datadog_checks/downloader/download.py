# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import glob
import logging
import logging.config
import os
import shutil
import tempfile

# Turn off TUF file logging.
import tuf.settings
tuf.settings.ENABLE_FILE_LOGGING = False

# Import what we need from TUF.
from tuf.client.updater import Updater

# Import what we need from in-toto.
from in_toto import verifylib
from in_toto.models.metadata import Metablock
from in_toto.util import import_public_keys_from_files_as_dict

# After we import everything we neeed, shut off all existing loggers.
logging.config.dictConfig({
    'disable_existing_loggers': True,
    'version': 1,
})

# NOTE: A module with a function that substitutes parameters for
# in-toto inspections. The function is expected to be called
# 'substitute', and takes one parameter, target_relpath, that specifies
# the relative target path of the given Python package. The function is
# expected to return a dictionary which maps parameter names to
# parameter values, so that in-toto can substitute these parameters in
# order to perform a successful inspection.
# The module is expected to live here.
from .parameters import substitute


# CONSTANTS.
here = os.path.abspath(os.path.dirname(__file__))
REPOSITORIES_DIR = os.path.join(here, 'data')
# abspath = os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR)
REPOSITORY_DIR = 'repo'
REPOSITORY_MIRRORS = {
    'repo': {
        'url_prefix': 'https://dd-integrations-core-wheels-build-stable.s3.amazonaws.com',
        'metadata_path': 'metadata.staged',
        'targets_path': 'targets',
        'confined_target_dirs': ['']
    }
}


# Global variables.
logger = logging.getLogger(__name__)


class TUFInTotoError(Exception):


    def __init__(self, target_relpath):
        self.target_relpath = target_relpath


    def __str__(self):
        return 'Unexpected tuf-in-toto error for {}!'.format(self.target_relpath)


class NoInTotoLinkMetadataFound(TUFInTotoError):


    def __str__(self):
        return 'in-toto link metadata expected, but not found for {}!'.format(self.target_relpath)


class NoInTotoRootLayoutPublicKeysFound(TUFInTotoError):


    def __str__(self):
        return 'in-toto root layout public keys expected, but not found for {}!'.format(self.target_relpath)


class TUFDownloader:


    def __init__(self, verbose=0):
        # 0 => 60 (effectively /dev/null)
        # 1 => 50 (CRITICAL)
        # 2 => 40 (ERROR)
        # 3 => 30 (WARNING)
        # 4 => 20 (INFO)
        # 5 => 10 (DEBUG)
        # And so it repeats from here...
        remainder = verbose % 6
        level = (6 - remainder) * 10
        assert level in range(10, 70, 10), level
        logging.basicConfig(format='%(levelname)-8s: %(message)s', level=level)

        tuf.settings.repositories_directory = REPOSITORIES_DIR

        # NOTE: The directory where the targets for *this* repository is
        # cached. We hard-code this keep this to a subdirectory dedicated to
        # this repository.
        self.__targets_dir = os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR, 'targets')

        # NOTE: Build a TUF updater which stores metadata in (1) the given
        # directory, and (2) uses the following mirror configuration,
        # respectively.
        # https://github.com/theupdateframework/tuf/blob/aa2ab218f22d8682e03c992ea98f88efd155cffd/tuf/client/updater.py#L628-L683
        # NOTE: This updater will store files under:
        # os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR)
        self.__updater = Updater(REPOSITORY_DIR, REPOSITORY_MIRRORS)

        # NOTE: Update to the latest top-level role metadata only ONCE, so that
        # we use the same consistent snapshot to download targets.
        self.__updater.refresh()


    def __download_in_toto_metadata(self, target):
        # A list to collect where in-toto metadata targets live.
        target_relpaths = []

        fileinfo = target.get('fileinfo')

        if fileinfo:
            custom = fileinfo.get('custom')

            if custom:
                in_toto_metadata = custom.get('in-toto')

                # A long but safe way of checking whether there is any in-toto
                # metadata embeddeed in an expected, hard-coded location.
                if in_toto_metadata:

                    for target_relpath in in_toto_metadata:
                        # Download the in-toto layout / link metadata file
                        # using TUF, which, among other things, prevents
                        # mix-and-match attacks by MitM attackers, and rollback
                        # attacks even by attackers who control the repository:
                        # https://www.usenix.org/conference/atc17/technical-sessions/presentation/kuppusamy
                        # NOTE: Avoid recursively downloading in-toto metadata
                        # for in-toto metadata themselves, and so on ad
                        # infinitum.
                        self.__get_target(target_relpath, download_in_toto_metadata=False)

                        # Add this file to the growing collection of where
                        # in-toto metadata live.
                        target_relpaths.append(target_relpath)

        # Return list of where in-toto metadata files live.
        return target_relpaths


    def __update_in_toto_layout_pubkeys(self):
        '''
        NOTE: We assume that all the public keys needed to verify any in-toto
        root layout, or sublayout, metadata file has been directly signed by
        the top-level TUF targets role using *OFFLINE* keys. This is a
        reasonable assumption, as TUF does not offer meaningful security
        guarantees if _ALL_ targets were signed using _online_ keys.
        '''

        target_relpaths = []
        targets = self.__updater.targets_of_role('targets')

        for target in targets:
            target_relpath = target['filepath']

            # Download this target only if it _looks_ like a public key.
            if target_relpath.endswith('.pub'):
                # NOTE: Avoid recursively downloading in-toto metadata for
                # in-toto root layout pubkeys themselves, and so on ad
                # infinitum.
                self.__get_target(target_relpath, download_in_toto_metadata=False)
                target_relpaths.append(target_relpath)

        return target_relpaths


    def __verify_in_toto_metadata(self, target_relpath, in_toto_metadata_relpaths, pubkey_relpaths):
        # Make a temporary directory.
        tempdir = tempfile.mkdtemp()
        prev_cwd = os.getcwd()

        try:
            # Copy files over into temp dir.
            rel_paths = [target_relpath] + in_toto_metadata_relpaths + pubkey_relpaths
            for rel_path in rel_paths:
                # Don't confuse Python with any leading path separator.
                rel_path = rel_path.lstrip('/')
                abs_path = os.path.join(self.__targets_dir, rel_path)
                shutil.copy(abs_path, tempdir)

            # Switch to the temp dir.
            os.chdir(tempdir)

            # Load the root layout and public keys.
            layout = Metablock.load('root.layout')
            pubkeys = glob.glob('*.pub')
            layout_key_dict = import_public_keys_from_files_as_dict(pubkeys)
            # Verify and inspect.
            params = substitute(target_relpath)
            verifylib.in_toto_verify(layout, layout_key_dict, substitution_parameters=params)
            logger.info('in-toto verified {}'.format(target_relpath))
        except:
            logger.exception('in-toto failed to verify {}'.format(target_relpath))
            raise
        finally:
            os.chdir(prev_cwd)
            # Delete temp dir.
            shutil.rmtree(tempdir)


    def __download_and_verify_in_toto_metadata(self, target, target_relpath):
        in_toto_metadata_relpaths = self.__download_in_toto_metadata(target)

        if not len(in_toto_metadata_relpaths):
            raise NoInTotoLinkMetadataFound(target_relpath)

        else:
            pubkey_relpaths = self.__update_in_toto_layout_pubkeys()

            if not len(pubkey_relpaths):
                raise NoInTotoRootLayoutPublicKeysFound(target_relpath)

            else:
                self.__verify_in_toto_metadata(target_relpath, in_toto_metadata_relpaths, pubkey_relpaths)


    def __get_target(self, target_relpath, download_in_toto_metadata=True):
        target = self.__updater.get_one_valid_targetinfo(target_relpath)
        updated_targets = self.__updater.updated_targets((target,), self.__targets_dir)

        # Either the target has not been updated...
        if not len(updated_targets):
            logger.debug('{} has not been updated'.format(target_relpath))
        # or, it has been updated, in which case...
        else:
            # First, we use TUF to download and verify the target.
            assert len(updated_targets) == 1
            updated_target = updated_targets[0]
            assert updated_target == target
            self.__updater.download_target(updated_target, self.__targets_dir)

        logger.info('TUF verified {}'.format(target_relpath))

        # Next, we use in-toto to verify the supply chain of the target.
        # NOTE: We use a flag to avoid recursively downloading in-toto
        # metadata for in-toto metadata themselves, and so on ad infinitum.
        # All other files, presumably packages, should also be
        # inspected.
        if download_in_toto_metadata:
            self.__download_and_verify_in_toto_metadata(target, target_relpath)
        else:
            logger.debug('Switched off in-toto verification for {}'.format(target_relpath))

        target_path = os.path.join(self.__targets_dir, target_relpath)
        return target_path


    def download(self, target_relpath, download_in_toto_metadata=True):
        '''
        Returns:
            If download over TUF and in-toto is successful, this function will
            return the complete filepath to the desired target.
        '''
        return self.__get_target(target_relpath, download_in_toto_metadata=download_in_toto_metadata)
