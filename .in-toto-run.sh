#!/bin/bash

# Bail on failure.
set -e -x

# Determine which gpg to call depending on OS.
KERNEL=$(uname -s)
if [ $KERNEL == "Linux" ]
then
  # If on Linux, assume we have gpg2.
  GPG=$(which gpg2)
else
  # Otherwise, assume we are on macOS, and have gpg2 installed via Homebrew.
  test $KERNEL == "Darwin"
  GPG=$(which gpg)
fi

# Get the keyid of the GPG key on Yubikey.
KEYID=$($GPG --card-status | grep -E 'sec(>|#)' | awk '{print $2}' | cut -f2 -d/)

# The fixed, hidden directory in the git repo where link metadata are kept.
LINK_DIR=.links

# The name of the in-toto step.
STEP_NAME=tag

# Record the (Yubikey-)signed hashes of all source files in this git repo.
in-toto-run -n $STEP_NAME -p . -g $KEYID -x

# Find this latest signed link metadata file on disk.
LATEST_TAG_LINK=$(ls -At $STEP_NAME.*.link | head -n 1)

# Remove previous, now obsolete versions of the link metadata.
git rm $LINK_DIR/*.$LATEST_TAG_LINK

# Recreate the directory to store link metadata, if necessary.
mkdir -p $LINK_DIR

# Get the timestamp associated with the latest link metadata.
TIMESTAMP=$(date +'%s' -r $LATEST_TAG_LINK)

# Copy the latest link metadata to a given location in the git repo.
mv $LATEST_TAG_LINK $LINK_DIR/$TIMESTAMP.$LATEST_TAG_LINK

# Add it to the git repo.
git add $LINK_DIR/$TIMESTAMP.$LATEST_TAG_LINK

# Commit it to the git repo.
git commit -S -m "Add latest tag link metadata."
