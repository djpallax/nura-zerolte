#!/usr/bin/env python3
"""Bounded TWRP ADB BOOT installer. Never formats or installs USERDATA."""
import argparse
import fcntl
import json
import os
import re
import select
import shutil
import subprocess
import sys
import termios
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
sys.dont_write_bytecode = True
from bootlib import BOOT, RECOVERY, CAPACITY, sha, require, parse_boot, repack_boot, load_bundle

ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w') as f:
        os.chmod(tmp, 0o600)
        json.dump(data, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


class Adb:
    def __init__(self, serial=None):
        devices = subprocess.check_output(['adb', 'devices'], timeout=10).decode().splitlines()[1:]
        devices = [line.split() for line in devices if line.strip()]
        if serial is None:
            require(len(devices) == 1 and devices[0][1] == 'recovery',
                    'Connect exactly one TWRP device, or select it explicitly with --serial')
            serial = devices[0][0]
        require(re.fullmatch(r'[A-Za-z0-9._:-]+', serial) is not None, 'Invalid ADB serial')
        self.serial = serial
        self.usb_port = None
        for node in Path('/sys/bus/usb/devices').glob('*'):
            try:
                if (node / 'serial').read_text().strip() == serial and (node / 'idVendor').read_text().strip() == '04e8':
                    self.usb_port = node.name
            except OSError:
                pass
        self.args = ['adb', '-s', serial]

    def run(self, *args, seconds=15, output=None):
        if output is not None:
            with output.open('xb') as f:
                subprocess.run(self.args + list(args), stdout=f, stderr=subprocess.PIPE,
                               timeout=seconds, check=True)
            return b''
        return subprocess.check_output(self.args + list(args), stderr=subprocess.PIPE, timeout=seconds)

    def shell(self, command, seconds=15):
        return self.run('shell', command, seconds=seconds).decode().strip()

    def identity(self):
        require(self.run('get-state', seconds=5).strip() == b'recovery', 'TWRP recovery required')
        require(self.shell('getprop ro.product.model') == 'SM-G925I', 'Unsupported phone model')
        require(self.shell('getprop ro.product.device') == 'zerolte', 'Unexpected device codename')
        require(bool(self.shell('getprop ro.twrp.version')), 'TWRP version property missing')
        require(self.shell('id -u') == '0', 'Recovery shell must be root')
        require(self.shell('readlink -f ' + BOOT) == '/dev/block/sda5', 'Unexpected BOOT target')
        require(self.shell('readlink -f ' + RECOVERY) == '/dev/block/sda6', 'Unexpected RECOVERY target')
        require(self.shell('cat /sys/class/block/sda5/size') == str(CAPACITY // 512), 'Wrong BOOT capacity')
        require(self.shell('blockdev --getro ' + BOOT) == '0', 'BOOT is read-only; no write attempted')
        token = 'NR_' + uuid.uuid4().hex
        require(self.shell('echo ' + token) == token, 'Recovery did not answer a unique probe')

    def readboot(self, destination):
        self.run('exec-out', 'dd if=' + BOOT + ' bs=1048576 count=28 2>/dev/null',
                 seconds=60, output=destination)
        data = destination.read_bytes()
        require(len(data) == CAPACITY, 'Incomplete BOOT read')
        return data

    def recovery_hash(self):
        result = self.shell('sha256sum ' + RECOVERY, seconds=60).split()
        require(result and re.fullmatch(r'[0-9a-f]{64}', result[0]), 'Invalid RECOVERY checksum')
        return result[0]


@contextmanager
def device_lock(serial):
    path = Path('/tmp') / ('nura-zerolte-' + str(os.getuid()) + '-' + sha(serial.encode())[:16] + '.lock')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def tty_for_phone(usb_port):
    for device in Path('/sys/class/tty').glob('ttyACM*'):
        for parent in (device / 'device').resolve().parents:
            try:
                if parent.name == usb_port and ((parent / 'idVendor').read_text().strip(), (parent / 'idProduct').read_text().strip()) == ('0525', 'a4a7'):
                    yield Path('/dev') / device.name
                    break
            except OSError:
                continue


def wait_linux(usb_port):
    require(usb_port is not None, 'Cannot correlate the USB port for boot monitoring; verify the installed phone manually')
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        for tty in tty_for_phone(usb_port):
            fd = None
            try:
                fd = os.open(tty, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                mode = termios.tcgetattr(fd)
                mode[0] = mode[1] = mode[3] = 0
                mode[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
                mode[4] = mode[5] = termios.B115200
                mode[6][termios.VMIN] = mode[6][termios.VTIME] = 0
                termios.tcsetattr(fd, termios.TCSANOW, mode)
                token = 'NR_LINUX_' + uuid.uuid4().hex
                half = len(token) // 2
                command = "\x03\rprintf '\\n%s%s\\n' '" + token[:half] + "' '" + token[half:] + "'\r"
                os.write(fd, command.encode())
                received = b''
                until = min(deadline, time.monotonic() + 6)
                while time.monotonic() < until:
                    if select.select([fd], [], [], max(0, min(1, until-time.monotonic())))[0]:
                        received = (received + os.read(fd, 8192))[-32768:]
                        if ('\n' + token + '\n').encode() in received.replace(b'\r', b''):
                            print('Linux USB BusyBox answered the unique probe.')
                            return
            except (OSError, BlockingIOError):
                pass
            finally:
                if fd is not None:
                    os.close(fd)
        time.sleep(1)
    raise TimeoutError('180 seconds without a valid Linux reply: stopped. No repeat flash or USB reset. Return to TWRP to restore.')


def write_once(adb, image, run, receipt):
    adb.identity()
    expected = sha(image.read_bytes())
    remote = '/tmp/nura-zerolte-' + uuid.uuid4().hex + '.img'
    adb.run('push', str(image), remote, seconds=60)
    require(adb.shell('sha256sum ' + remote, seconds=30).split()[0] == expected, 'Push checksum mismatch')
    receipt['candidate'] = image.name
    receipt['candidate_sha256'] = expected
    receipt['write_attempted'] = True
    save(run / 'receipt.json', receipt)  # Durable marker before the one BOOT write.
    adb.shell('dd if=' + remote + ' of=' + BOOT + ' bs=1048576 count=28 && sync', seconds=60)
    readback = adb.readboot(run / 'BOOT-readback.img')
    require(sha(readback) == expected, 'BOOT readback mismatch: no reboot or automatic retry')
    require(adb.recovery_hash() == receipt['recovery_sha256'], 'RECOVERY checksum changed: stop')
    receipt['verified'] = True
    save(run / 'receipt.json', receipt)
    adb.shell('rm -f ' + remote)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'install', 'restore'])
    parser.add_argument('--bundle', type=Path, default=ROOT / 'dist/zerolte')
    parser.add_argument('--backup-dir', type=Path, default=ROOT / 'private/backups')
    parser.add_argument('--receipt', type=Path, help='Required for restore: original installation receipt.json')
    parser.add_argument('--serial')
    parser.add_argument('--reboot', action='store_true', help='Reboot only after verified install; wait <=180s for USB Linux reply')
    a = parser.parse_args()
    manifest = loader = None
    original = None
    if a.action != 'restore':
        manifest, loader = load_bundle(a.bundle)
        lock = json.loads((Path(__file__).resolve().parents[1] / "sources.lock.json").read_text())
        require(manifest.get("kernel_source_tree") == lock["kernel"]["source_tree"], "Bundle has a different kernel source tree")
        require(manifest.get("loader_commit") == lock["uniloader"]["commit"], "Bundle has a different loader revision")
    else:
        require(a.receipt is not None, 'Restore requires --receipt')
    adb = Adb(a.serial)
    with device_lock(adb.serial):
        adb.identity()
        a.backup_dir.mkdir(parents=True, exist_ok=True)
        require(shutil.disk_usage(a.backup_dir).free >= 5 * CAPACITY, 'Insufficient backup space')
        # Do not retry a previous uncertain write on this phone automatically.
        for previous in a.backup_dir.glob('*/receipt.json'):
            record = json.loads(previous.read_text())
            if record.get('serial') == adb.serial and record.get('write_attempted') and not record.get('verified') and not record.get('resolved_by_restore'):
                require(a.action == 'restore', 'An earlier write is unverified. Inspect its receipt and restore first.')
        run = a.backup_dir / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
        run.mkdir(mode=0o700)
        recovery_hash = adb.recovery_hash()
        before = adb.readboot(run / 'BOOT-before.img')
        require(sha(before) == sha(adb.readboot(run / 'BOOT-before-confirm.img')), 'BOOT changed during backup')
        parse_boot(before)
        (run / 'BOOT-before.img').chmod(0o400)
        receipt = {'schema': 1, 'model': 'SM-G925I', 'serial': adb.serial,
                   'backup': 'BOOT-before.img', 'backup_sha256': sha(before),
                   'recovery_sha256': recovery_hash, 'write_attempted': False, 'verified': False,
                   'action': a.action, 'usb_port': adb.usb_port}
        save(run / 'receipt.json', receipt)
        if a.action == 'restore':
            original = json.loads(a.receipt.read_text())
            require(original.get('schema') == 1 and original.get('model') == 'SM-G925I', 'Invalid restore receipt')
            require(original['serial'] == adb.serial, 'Backup belongs to a different phone')
            require(original['backup'] == 'BOOT-before.img', 'Invalid backup filename')
            source = a.receipt.parent / original['backup']
            require(not source.is_symlink(), 'Backup symlinks are not permitted')
            data = source.read_bytes()
            parse_boot(data)
            require(sha(data) == original['backup_sha256'], 'Backup checksum mismatch')
            image = run / 'BOOT-restore.img'
            image.write_bytes(data)
        else:
            image = run / 'BOOT-candidate.img'
            image.write_bytes(repack_boot(before, loader))
            receipt['root_mode'] = manifest['root_mode']
            save(run / 'receipt.json', receipt)
        print('Private backup and receipt:', run)
        if a.action == 'check':
            print('Preflight passed. Candidate fits; no partition was written and no reboot requested.')
            return
        if image.read_bytes() == before:
            receipt.update(verified=True, no_write_needed=True, candidate=image.name, candidate_sha256=sha(before))
            save(run / 'receipt.json', receipt)
            print('BOOT already matches; no write performed.')
        else:
            write_once(adb, image, run, receipt)
        if original is not None:
            original['resolved_by_restore'] = str((run / 'receipt.json').resolve())
            save(a.receipt, original)
        print('BOOT verified; RECOVERY unchanged. USERDATA was not written.')
        if a.reboot:
            adb.run('reboot', seconds=10)
            if a.action != 'restore':
                wait_linux(adb.usb_port)
            else:
                print('Original BOOT restored; reboot sent. Original OS may not provide CDC ACM.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, TimeoutError) as exc:
        print('STOP:', str(exc), file=sys.stderr)
        sys.exit(1)
