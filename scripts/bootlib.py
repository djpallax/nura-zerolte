"""Pure Samsung legacy-BOOT packaging and bundle validation; no device access."""
import gzip
import hashlib
import json
import stat
import struct
from pathlib import Path

CAPACITY = 28 * 1024 * 1024
BOOT = '/dev/block/platform/15570000.ufs/by-name/BOOT'
RECOVERY = '/dev/block/platform/15570000.ufs/by-name/RECOVERY'
FLOOR = 12 * 1024**3


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def image64(data):
    require(len(data) >= 64 and data[56:60] == b'ARM\x64', 'Not an ARM64 Image/loader')


def parse_boot(data):
    require(len(data) == CAPACITY and data[:8] == b'ANDROID!', 'Wrong BOOT size/magic')
    v = struct.unpack_from('<10I', data, 8)
    ks, ka, rs, ra, ss, sa, ta, page, ds, unused = v
    require((ka, ra, sa, ta, page, unused) ==
            (0x10008000, 0x11000000, 0x10f00000, 0x10000100, 2048, 0),
            'Unsupported Samsung legacy BOOT layout; no write allowed')
    require(ks > 0 and ss == 0, 'Unsupported BOOT component layout')
    pos = page
    chunks = []
    for size in (ks, rs, ss, ds):
        require(size <= CAPACITY and pos + size <= CAPACITY, 'Truncated BOOT component')
        chunks.append(data[pos:pos + size])
        pos += (size + page - 1) // page * page
    require(pos <= CAPACITY, 'BOOT component alignment exceeds partition')
    return data[:page], chunks, data[pos:].rstrip(b'\0')


def repack_boot(template, loader):
    image64(loader)
    header, chunks, tail = parse_boot(template)
    chunks[0] = loader
    header = bytearray(header)
    digest = hashlib.sha1()
    for offset, chunk in zip((8, 16, 24, 40), chunks):
        struct.pack_into('<I', header, offset, len(chunk))
        digest.update(chunk)
        digest.update(struct.pack('<I', len(chunk)))
    header[576:608] = digest.digest() + bytes(12)
    page = len(header)
    data = bytes(header) + b''.join(c + bytes(-len(c) % page) for c in chunks) + tail
    require(len(data) <= CAPACITY, 'Payload and preserved Samsung data do not fit BOOT')
    result = data + bytes(CAPACITY - len(data))
    # Owner-specific outer ramdisk, Samsung DT tables and opaque footer survive.
    _, actual, actual_tail = parse_boot(result)
    require(actual == chunks and actual_tail == tail, 'BOOT repack preservation failed')
    return result


def newc(entries):
    """Deterministic root-owned cpio; regular files, directories and symlinks only."""
    result = bytearray()
    entries = list(entries) + [('TRAILER!!!', stat.S_IFREG, b'')]
    for ino, (name, mode, body) in enumerate(entries, 1):
        require(not name.startswith('/') and '..' not in Path(name).parts, 'Unsafe cpio name')
        name = name.encode() + b'\0'
        h = [ino, mode, 0, 0, 1, 0, len(body), 0, 0, 0, 0, len(name), 0]
        result += b'070701' + b''.join(f'{v:08x}'.encode() for v in h) + name
        result += bytes(-len(result) % 4) + body
        result += bytes(-len(result) % 4)
    result += bytes(-len(result) % 512)
    return gzip.compress(result, compresslevel=6, mtime=0)


def load_bundle(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root / 'manifest.json').read_text())
    require(manifest.get('schema') == 1 and manifest.get('model') == 'SM-G925I', 'Wrong bundle model/schema')
    require(manifest.get('root_mode') in ('rescue', 'userdata'), 'Invalid root mode')
    require(manifest.get('partition_bytes') == CAPACITY, 'Wrong BOOT capacity')
    required = {'uniLoader', 'Image', 'zerolte.dtb', 'initramfs.cpio.gz'}
    require(set(manifest['files']) == required, 'Unexpected bundle file set')
    for name, record in manifest['files'].items():
        path = root / name
        require(not path.is_symlink(), 'Bundle symlinks are not permitted')
        data = path.read_bytes()
        require(len(data) == record['bytes'] and sha(data) == record['sha256'], 'Bundle hash/size mismatch: ' + name)
    loader = (root / 'uniLoader').read_bytes()
    image64(loader)
    image64((root / 'Image').read_bytes())
    for name in required - {'uniLoader'}:
        require((root / name).read_bytes() in loader, 'Loader does not embed ' + name)
    return manifest, loader
