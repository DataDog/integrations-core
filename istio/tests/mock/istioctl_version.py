import sys

if __name__ == "__main__":
    assert '--short' in sys.argv
    assert '--remote=false' in sys.argv
    version = sys.argv[1]
    print(version)
