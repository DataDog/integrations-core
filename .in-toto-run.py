#!/usr/bin/env python3

import os
import shlex
import shutil
import subprocess

# pip3 install in-toto>=0.2.dev3
import in_toto.gpg
import in_toto.runlib as runlib
import in_toto.settings

# CONSTANTS.

# The name of the in-toto step.
STEP_NAME = "tag"

# Functions.

# Get the keyid of the GPG key on Yubikey.
def getKeyId():
    # Determine which gpg to call depending on OS.
    def getGPGExec():
        sysname = os.uname().sysname

        # If on Linux, assume we have gpg2.
        if sysname == "Linux":
            gpg = "gpg2"
        elif sysname == "Darwin":
            gpg = "gpg"
        else:
            raise Exception("{} not supported!".format(sysname))

        return gpg


    cmd = shlex.split("{} --card-status".format(getGPGExec()))
    output = subprocess.check_output(cmd)
    lines = output.decode("utf-8").split("\n")
    for line in lines:
        if line.startswith('Signature key ....:'):
            return line.split(':')[1].replace(' ', '')
    else:
        raise Exception("Could not find private signing key on Yubikey!")


# Record the (Yubikey-)signed hashes of all source files in this git repo.
def runInToto(keyId):
    def load_gitignore(filename = '.gitignore'):
        exclude_patterns = []

        with open(filename) as gitignore:
            for line in gitignore:
                line = line.strip()
                if line and not line.startswith('#'):
                    exclude_patterns.append(line)

        return exclude_patterns


    # NOTE: Exclude anything that looks like the following patterns.
    exclude_patterns = list(set(in_toto.settings.ARTIFACT_EXCLUDE_PATTERNS + \
                                load_gitignore()))

    # TODO: Would be nice to pass to in-toto the GPG executable to call.
    inTotoCmd = runlib.in_toto_run(
        # Do NOT record files matching these patters.
        exclude_patterns = exclude_patterns,
        # Use this GPG key.
        gpg_keyid = keyId,
        # Do NOT execute any other command.
        link_cmd_args = [],
        # Do NOT record anything as input.
        material_list = None,
        # Use this step name.
        name = STEP_NAME,
        # Do record every source file, except for exclude_patterns, as output.
        product_list = "."
    )


def addToGit(keyId):
    # The fixed, hidden directory in the git repo where link metadata are kept.
    LINK_DIR = ".links"

    # Where we tell the pipeline where to find the latest tag link metadata.
    LATEST_TAG_LINK = os.path.join(LINK_DIR, 'LATEST')

    # Recreate the directory to store link metadata, if necessary.
    if not os.path.exists(LINK_DIR):
        os.mkdir(LINK_DIR)
    elif not os.path.isdir(LINK_DIR):
        raise Exception("{LINK_DIR} already exists and "
                        "it's not a directory!".format(LINK_DIR))

    # Find this latest signed link metadata file on disk.
    # NOTE: in-toto currently uses the first 8 characters of the signing keyId.
    keyIdPrefix = keyId[:8].lower()
    tag_link = "{}.{}.link".format(STEP_NAME, keyIdPrefix)
    assert os.path.isfile(tag_link)

    # Tell pipeline which tag link metadata to use.
    with open(LATEST_TAG_LINK, 'wt') as latest:
        latest.write(tag_link)

    # Move it to the expected location.
    moved_tag_link = os.path.join(LINK_DIR, tag_link)
    shutil.move(tag_link, moved_tag_link)

    # Add files to the git repo.
    gitAddCmd = shlex.split("git add -f {} {}".format(moved_tag_link,
                                                      LATEST_TAG_LINK))
    subprocess.check_call(gitAddCmd)

    # Commit it to the git repo.
    gitCommitCmd = shlex.split("git commit -S -m 'Add tag link metadata.'")
    subprocess.check_call(gitCommitCmd)


# One function to compose them all.
if __name__ == '__main__':
    keyId = getKeyId()
    runInToto(keyId)
    addToGit(keyId)
