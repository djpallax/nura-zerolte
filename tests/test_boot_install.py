"""Offline image-preservation and installer refusal/rollback tests."""
import gzip
import hashlib
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from bootlib import CAPACITY, parse_boot, repack_boot, newc, sha


def arm64(body=b''):
    header = bytearray(64); header[56:60] = b'ARM\x64'
    return bytes(header) + body


def template():
    header = bytearray(2048); header[:8] = b'ANDROID!'
    chunks = [arm64(b'owner-original'), b'OWNER-OUTER-RAMDISK', b'', b'OWNER-SAMSUNG-DT-TABLE']
    struct.pack_into('<10I', header, 8, len(chunks[0]), 0x10008000,
                     len(chunks[1]), 0x11000000, 0, 0x10f00000, 0x10000100,
                     2048, len(chunks[3]), 0)
    digest = hashlib.sha1()
    for c in chunks:
        digest.update(c); digest.update(struct.pack('<I', len(c)))
    header[576:608] = digest.digest() + bytes(12)
    data = bytes(header) + b''.join(c + bytes(-len(c) % 2048) for c in chunks) + b'OPAQUE-OWNER-FOOTER'
    return data + bytes(CAPACITY - len(data))


class Packaging(unittest.TestCase):
    def test_preserves_owner_components_and_footer(self):
        before = template(); payload = arm64(b'new-payload')
        after = repack_boot(before, payload)
        _, old, tail = parse_boot(before); h, new, newtail = parse_boot(after)
        self.assertEqual(new, [payload] + old[1:]); self.assertEqual(tail, newtail)
        self.assertEqual(len(after), CAPACITY)
        digest = hashlib.sha1()
        for c in new: digest.update(c); digest.update(struct.pack('<I', len(c)))
        self.assertEqual(h[576:596], digest.digest())
        self.assertEqual(repack_boot(after, payload), after)

    def test_refuses_foreign_header_and_oversize_payload(self):
        data = bytearray(template()); struct.pack_into('<I', data, 36, 4096)
        with self.assertRaises(ValueError): repack_boot(bytes(data), arm64())
        with self.assertRaises(ValueError): repack_boot(template(), arm64(bytes(CAPACITY)))

    def test_cpio_is_deterministic_and_rejects_traversal(self):
        items = [('init', stat.S_IFREG | 0o755, b'#!/bin/sh\n')]
        self.assertEqual(newc(items), newc(items))
        self.assertTrue(gzip.decompress(newc(items)).startswith(b'070701'))
        with self.assertRaises(ValueError): newc([('../escape', stat.S_IFREG, b'x')])


class Installer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='s6-offline-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.device = self.root / 'device'; self.device.mkdir()
        (self.device / 'boot.img').write_bytes(template())
        self.initial = sha(template())
        self.state = {'writes': 0, 'reboots': 0, 'recovery_hash': sha(b'unchanged-recovery')}
        self.write_state()
        tools = self.root/'tools'; tools.mkdir()
        shutil.copyfile(ROOT/'tests/fake_adb.py', tools/'adb'); (tools/'adb').chmod(0o755)
        self.env = dict(os.environ, PATH=str(tools)+os.pathsep+os.environ['PATH'], S6_FAKE_ADB=str(self.device))
        self.bundle = self.root/'bundle'; self.bundle.mkdir()
        image = arm64(b'kernel'); dtb = b'fake-unit-test-dtb'; initrd = newc([('init', stat.S_IFREG | 0o755, b'shell')])
        files = {'Image': image, 'zerolte.dtb': dtb, 'initramfs.cpio.gz': initrd,
                 'uniLoader': arm64(b'loader'+image+dtb+initrd)}
        lock = json.loads((ROOT/'sources.lock.json').read_text())
        manifest = {'schema': 1, 'model': 'SM-G925I', 'root_mode': 'rescue', 'partition_bytes': CAPACITY,
                    'kernel_source_tree': lock['kernel']['source_tree'], 'loader_commit': lock['uniloader']['commit'],
                    'files': {n: {'bytes': len(b), 'sha256': sha(b)} for n,b in files.items()}}
        for n,b in files.items(): (self.bundle/n).write_bytes(b)
        (self.bundle/'manifest.json').write_text(json.dumps(manifest))
        self.backups = self.root/'private-backups'

    def write_state(self): (self.device/'state.json').write_text(json.dumps(self.state))
    def read_state(self): return json.loads((self.device/'state.json').read_text())
    def run_install(self, action='install', extra=()):
        return subprocess.run([sys.executable, str(ROOT/'scripts/install.py'), action,
                               '--bundle', str(self.bundle), '--backup-dir', str(self.backups), *extra],
                              env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    def receipt(self): return next(self.backups.glob('*/receipt.json'))

    def test_check_never_writes_or_reboots(self):
        result = self.run_install('check', ['--reboot'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_state()['writes'], 0); self.assertEqual(self.read_state()['reboots'], 0)
        self.assertEqual(sha((self.device/'boot.img').read_bytes()), self.initial)

    def test_install_backs_up_verifies_and_restores(self):
        result = self.run_install(); self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_state()['writes'], 1)
        receipt = self.receipt(); record = json.loads(receipt.read_text())
        self.assertTrue(record['verified']); self.assertEqual(record['backup_sha256'], self.initial)
        self.assertEqual(sha((receipt.parent/'BOOT-before.img').read_bytes()), self.initial)
        result = self.run_install('restore', ['--receipt', str(receipt)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sha((self.device/'boot.img').read_bytes()), self.initial)
        self.assertEqual(self.read_state()['writes'], 2)

    def test_wrong_model_refused_before_write(self):
        self.state['model'] = 'UNSUPPORTED'; self.write_state()
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual(self.read_state()['writes'], 0)

    def test_corrupt_bundle_refused_before_any_adb_call(self):
        (self.bundle/'Image').write_bytes(b'bad')
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertNotIn('calls', self.read_state())

    def test_bad_push_does_not_flash(self):
        self.state['bad_push'] = True; self.write_state()
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual(self.read_state()['writes'], 0)

    def test_bad_readback_blocks_reboot_and_retry(self):
        self.state['corrupt_readback'] = True; self.write_state()
        self.assertNotEqual(self.run_install(extra=['--reboot']).returncode, 0)
        self.assertEqual(self.read_state()['writes'], 1); self.assertEqual(self.read_state()['reboots'], 0)
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual(self.read_state()['writes'], 1)
        original = self.receipt()
        current = self.read_state(); current['corrupt_readback'] = False
        (self.device/'state.json').write_text(json.dumps(current))
        result = self.run_install('restore', ['--receipt', str(original)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sha((self.device/'boot.img').read_bytes()), self.initial)
        self.assertIn('resolved_by_restore', json.loads(original.read_text()))

    def test_already_installed_does_not_flash_again(self):
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(self.read_state()['writes'], 1)

    def test_wrong_partition_capacity_is_refused(self):
        self.state['capacity'] = '999'; self.write_state()
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual(self.read_state()['writes'], 0)

    def test_multiple_devices_require_explicit_selection(self):
        self.state['devices'] = 'List of devices attached\nTESTDEVICE\trecovery\nSECOND\trecovery'
        self.write_state()
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual(self.read_state()['writes'], 0)

    def test_tampered_backup_is_not_restored(self):
        self.assertEqual(self.run_install().returncode, 0)
        receipt = self.receipt(); backup = receipt.parent / 'BOOT-before.img'
        backup.chmod(0o600)
        body = bytearray(backup.read_bytes()); body[3000] ^= 1; backup.write_bytes(body)
        result = self.run_install('restore', ['--receipt', str(receipt)])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.read_state()['writes'], 1)

    def test_write_failure_stops_without_retry_or_reboot(self):
        self.state['write_failure'] = True; self.write_state()
        self.assertNotEqual(self.run_install(extra=['--reboot']).returncode, 0)
        self.assertEqual(self.read_state()['writes'], 1); self.assertEqual(self.read_state()['reboots'], 0)


if __name__ == '__main__':
    unittest.main()
