from ddev.config.file import ConfigFile


def main():
    config = ConfigFile()
    config.load()

    print(f'ddev{{repo: {config.model.repo.name}, org: {config.model.org.name}}}')
