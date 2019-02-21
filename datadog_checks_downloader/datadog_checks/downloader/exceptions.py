# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# Exceptions for the CLI module.


class CLIError(Exception):


    def __init__(self, standard_distribution_name):
        self.standard_distribution_name = standard_distribution_name


    def __str__(self):
        return 'Unexpected CLI error for {}!'.format(self.standard_distribution_name)


class InconsistentSimpleIndex(CLIError):


    def __init__(self, href, text):
        self.href = href
        self.text = text


    def __str__(self):
        return '{} != {}'.format(self.href, self.text)


class MissingVersions(CLIError):


    def __str__(self):
        return 'No version found for {} !'.format(self.standard_distribution_name)


class NonCanonicalVersion(CLIError):


    def __init__(self, version):
        self.version = version


    def __str__(self):
        return '{} is not a valid PEP 440 version!'.format(self.version)


class NonDatadogPackage(CLIError):


    def __str__(self):
        return '{} is not a Datadog package!'.format(self.standard_distribution_name)


class NoSuchDatadogPackage(CLIError):


    def __str__(self):
        return 'Could not find the {} package!'.format(self.standard_distribution_name)


class NoSuchDatadogPackageOrVersion(CLIError):


    def __init__(self, standard_distribution_name, version):
        super(NoSuchDatadogPackageOrVersion, self).__init__(standard_distribution_name)
        self.version = version


    def __str__(self):
        return 'Either no {} package, or {} version!'.format(self.standard_distribution_name, self.version)


# Exceptions for the download module.


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
