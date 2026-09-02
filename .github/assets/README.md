# Assets

Images referenced from content GitHub renders, rather than from any shipped code.

## Progress bar pixels

The four `progress-*.png` files are each a 1x1 PNG of one solid colour from GitHub's palette. The
Dispatcher pull-request comment (`ddev/src/ddev/cli/ci/tests/pr_comment.py`) draws its progress bar by
scaling them with the `width` attribute, one image per segment:

```html
<img src=".../progress-passed.png" width="120" height="10" alt=""><img src=".../progress-pending.png" width="120" height="10" alt="">
```

Scaling a single-colour pixel is lossless, so the bar can be any width without a file per size. GitHub's
markdown sanitizer allows neither a `progress` element nor a data URI in `src`, which rules out the
alternatives.

To change a colour, regenerate the file:

```python
import struct, zlib

COLORS = {
    "progress-passed": (31, 136, 61),
    "progress-failed": (207, 34, 46),
    "progress-skipped": (154, 103, 0),
    "progress-pending": (209, 217, 224),
}

def chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

for name, rgb in COLORS.items():
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8-bit, truecolor
    idat = zlib.compress(bytes([0]) + bytes(rgb))
    with open(f".github/assets/{name}.png", "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))
```
