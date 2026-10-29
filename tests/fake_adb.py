#!/usr/bin/env python3
"""Offline ADB simulator used only by the installer tests. Never calls real adb."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

root = Path(os.environ['S6_FAKE_ADB'])
state_path = root / 'state.json'
state = json.loads(state_path.read_text())
args = sys.argv[1:]
state.setdefault('calls', []).append(args)

def save():
    state_path.write_text(json.dumps(state))

def out(value):
    save()
    sys.stdout.write(value + '\n')
    sys.exit(0)

if args == ['devices']:
    out(state.get('devices', 'List of devices attached\nTESTDEVICE\trecovery'))
if args[:2] != ['-s', 'TESTDEVICE']:
    save(); sys.exit(2)
args = args[2:]
if args == ['get-state']:
    out('recovery')
if args[0] == 'push':
    shutil.copyfile(args[1], root / 'pushed.img')
    out('1 file pushed')
if args[0] == 'reboot':
    state['reboots'] += 1
    out('')
if args[0] == 'exec-out' and args[1].startswith('dd if='):
    save()
    sys.stdout.buffer.write((root / 'boot.img').read_bytes())
    sys.exit(0)
if args[0] != 'shell':
    save(); sys.exit(2)
command = args[1]
values = {'getprop ro.product.model': state.get('model', 'SM-G925I'),
          'getprop ro.product.device': 'zerolte', 'getprop ro.twrp.version': 'test-recovery',
          'id -u': '0', 'cat /sys/class/block/sda5/size': state.get('capacity', '57344')}
if command in values:
    out(values[command])
if command.startswith('echo '):
    out(command[5:])
if command.startswith('readlink -f '):
    out('/dev/block/sda5' if command.endswith('/BOOT') else '/dev/block/sda6')
if command.startswith('blockdev --getro '):
    out('0')
if command.startswith('sha256sum '):
    value = state['recovery_hash'] if command.endswith('/RECOVERY') else hashlib.sha256((root/'pushed.img').read_bytes()).hexdigest()
    if state.get('bad_push') and not command.endswith('/RECOVERY'):
        value = '0' * 64
    out(value + '  checked-file')
if command.startswith('dd if=/tmp/'):
    state['writes'] += 1
    shutil.copyfile(root / 'pushed.img', root / 'boot.img')
    if state.get('corrupt_readback'):
        data = bytearray((root/'boot.img').read_bytes()); data[2048] ^= 1; (root/'boot.img').write_bytes(data)
    if state.get('write_failure'):
        save(); sys.exit(1)
    out('')
if command.startswith('rm -f /tmp/'):
    out('')
save()
sys.exit(2)
