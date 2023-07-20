from fnmatch import fnmatch
import sys
import json
import hashlib


def compute_sha256(filename):
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def error(*args):
    print(*args, file=sys.stderr)
    sys.exit(1)


updated_link_files = [f for f in sys.argv[1:] if fnmatch(f, '.in-toto/tag.*.link')]
if not updated_link_files:
    error("The release-hash-check should only run upon modification of a link file.")
if len(updated_link_files) > 1:
    error("There should never be two different link files modified at the same time.")

link_file = updated_link_files[0]
with open(link_file, 'r') as f:
    content = json.load(f)

products = content['signed']['products']

for product, signatures in products.items():
    expected_sha = signatures['sha256']
    if expected_sha != compute_sha256(product):
        error(
            f"File {product} currently has a different sha than what has been signed. "
            f"Is your branch up to date with master?"
        )

print(f"Link file {link_file} has valid signatures.")
