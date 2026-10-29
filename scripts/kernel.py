#!/usr/bin/env python3
"""Reconstruct the pinned development kernel; never contacts a device."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'sources.lock.json').read_text())['kernel']
FLOOR = 12 * 1024**3


def run(*args, **kwargs):
    return subprocess.run(args, check=True, timeout=120, **kwargs)


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], timeout=30)


def space(path):
    if shutil.disk_usage(path).free < FLOOR:
        raise SystemExit('Stopped: less than 12 GiB available; nothing deleted.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['check', 'prepare', 'verify', 'build'])
    p.add_argument('source', type=Path)
    p.add_argument('output', nargs='?', type=Path)
    a = p.parse_args()
    source = a.source.resolve()
    patch = ROOT / LOCK['patch']
    config = ROOT / LOCK['config']
    assert hashlib.sha256(patch.read_bytes()).hexdigest() == LOCK['patch_sha256']
    assert hashlib.sha256(config.read_bytes()).hexdigest() == LOCK['config_sha256']
    head = git(source, 'rev-parse', 'HEAD').decode().strip()
    if a.action in ('check', 'prepare'):
        assert head == LOCK['base_commit'], 'Patch preparation requires the upstream base'
        assert not git(source, 'status', '--porcelain').strip(), 'Use a clean disposable checkout'
        run('git', '-C', str(source), 'apply', '--check', str(patch))
        if a.action == 'prepare':
            run('git', '-C', str(source), 'apply', '--index', str(patch))
        print('Patch matches pinned kernel base; action:', a.action)
        return
    # Accept either the clean fork snapshot or the exact prepared fallback patch.
    committed = git(source, 'rev-parse', 'HEAD^{tree}').decode().strip() == LOCK['source_tree']
    if committed:
        assert not git(source, 'status', '--porcelain').strip(), 'Fork checkout must be clean'
    else:
        assert head == LOCK['base_commit'], 'Source is not the pinned fork snapshot or upstream base'
        assert git(source, 'diff', '--binary', '--full-index', 'HEAD') == patch.read_bytes(), 'Source delta differs'
        assert not git(source, 'ls-files', '--others', '--exclude-standard').strip(), 'Untracked files present'
    if a.action == 'verify':
        print('Source matches the locked publication snapshot; no build performed.')
        return
    if a.output is None:
        p.error('build requires an empty output directory')
    output = a.output.resolve()
    assert not output.exists(), 'Use a new output directory'
    assert source not in output.parents and output != source, 'Use an out-of-tree build'
    space(output.parent)
    output.mkdir()
    shutil.copyfile(config, output / '.config')
    for tool in ['clang', 'ld.lld', 'make', 'dtc']:
        assert shutil.which(tool), 'Missing tool: ' + tool
    run('make', '-C', str(source), 'O=' + str(output), 'ARCH=arm64', 'LLVM=1', 'olddefconfig')
    command = ['make', '-C', str(source), 'O=' + str(output), 'ARCH=arm64', 'LLVM=1', '-j4', 'Image']
    proc = subprocess.Popen(command, start_new_session=True)
    started = time.monotonic()
    try:
        while proc.poll() is None:
            space(output)
            if time.monotonic() - started > 1800:
                raise SystemExit('Kernel build exceeded 30 minutes')
            time.sleep(5)
        if proc.returncode:
            raise SystemExit(proc.returncode)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
    space(output)
    run('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(output / 'zerolte-system2.dtb'), str(ROOT / 'kernel/zerolte-system2.dts'))
    space(output)
    print('Image and DTB built. No loader, BOOT or rootfs package generated.')


if __name__ == '__main__':
    main()
