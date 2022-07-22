# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# Exceptions for the CLI module.


class ChecksDownloaderException(Exception):
    """A top level exception type for datadog-checks-downloader module."""


class CLIError(ChecksDownloaderException):
    pass


class NonCanonicalVersion(CLIError):
    def __init__(self, version):
        self.version = version

    def __str__(self):
        return '{}'.format(self.version)


class NonDatadogPackage(CLIError):
    def __init__(self, standard_distribution_name):
        self.standard_distribution_name = standard_distribution_name

    def __str__(self):
        return '{}'.format(self.standard_distribution_name)


# Exceptions for the download module.


class UpdatedTargetsError(ChecksDownloaderException):
    """An exception raised when any issue with updated target arises."""


class IncorrectRootLayoutType(ChecksDownloaderException):
    def __init__(self, found, expected):
        self.found = found
        self.expected = expected

    def __str__(self):
        return (
            "Incorrect type, found {}, expected {}. "
            "Make sure to use the -t/--third-party flag when (and only when) downloading third-party integrations."
            "".format(self.found, self.expected)
        )


class SimpleIndexError(ChecksDownloaderException):
    def __init__(self, standard_distribution_name):
        self.standard_distribution_name = standard_distribution_name

    def __str__(self):
        return '{}'.format(self.standard_distribution_name)


class MissingVersions(SimpleIndexError):
    pass


class NoSuchDatadogPackage(SimpleIndexError):
    pass


class InconsistentSimpleIndex(SimpleIndexError):
    def __init__(self, href, text):
        self.href = href
        self.text = text

    def __str__(self):
        return '{}: {}!={}'.format(self.standard_distribution_name, self.href, self.text)


class NoSuchDatadogPackageVersion(SimpleIndexError):
    def __init__(self, standard_distribution_name, version):
        super(NoSuchDatadogPackageVersion, self).__init__(standard_distribution_name)
        self.version = version

    def __str__(self):
        return '{}-{}'.format(self.standard_distribution_name, self.version)


class DuplicatePackage(SimpleIndexError):
    def __init__(self, standard_distribution_name, version, python_tag):
        super(DuplicatePackage, self).__init__(standard_distribution_name)
        self.version = version
        self.python_tag = python_tag

    def __str__(self):
        return '{}-{}-{}'.format(self.standard_distribution_name, self.version, self.python_tag)


class PythonVersionMismatch(SimpleIndexError):
    def __init__(self, standard_distribution_name, version, this_python, python_tags):
        super(PythonVersionMismatch, self).__init__(standard_distribution_name)
        self.version = version
        self.this_python = this_python
        self.python_tags = python_tags

    def __str__(self):
        return '{}-{}: {} not in {}'.format(
            self.standard_distribution_name, self.version, self.this_python, self.python_tags
        )


class TUFInTotoError(ChecksDownloaderException):
    def __init__(self, target_relpath):
        self.target_relpath = target_relpath

    def __str__(self):
        return '{}'.format(self.target_relpath)


class NoInTotoLinkMetadataFound(TUFInTotoError):
    pass


class NoInTotoRootLayoutPublicKeysFound(TUFInTotoError):
    pass


class RevokedDeveloperOrMachine(TUFInTotoError):
    MSG = "Step 'tag' requires '1' link metadata file(s), found '0'."

    def __init__(self, target_relpath, in_toto_root_layout):
        super(RevokedDeveloperOrMachine, self).__init__(target_relpath)
        self.in_toto_root_layout = in_toto_root_layout

    def __str__(self):
        return '{} ({})'.format(self.target_relpath, self.in_toto_root_layout)
