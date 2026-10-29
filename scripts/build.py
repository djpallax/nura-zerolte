#!/usr/bin/env python3
"""Build a clean kernel/loader/rescue bundle. Does not access a phone."""
import argparse
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path
sys.dont_write_bytecode = True
from bootlib import FLOOR, CAPACITY, sha, require, image64, newc, load_bundle

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'sources.lock.json').read_text())


def space(path):
    require(shutil.disk_usage(path).free >= FLOOR, 'Less than 12 GiB free; stopped without deleting files')


def run(args, log, cwd=None, seconds=600):
    space(log.parent)
    with log.open('wb') as output:
        process = subprocess.Popen([str(x) for x in args], cwd=cwd, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + seconds
        try:
            while process.poll() is None:
                space(log.parent)
                require(time.monotonic() < deadline, 'Command timed out; see ' + str(log))
                time.sleep(2)
            require(process.returncode == 0, 'Command failed; see ' + str(log))
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
    space(log.parent)


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], timeout=30).decode().strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel', type=Path, required=True)
    p.add_argument('--work', type=Path, default=ROOT / 'build')
    p.add_argument('--output', type=Path, default=ROOT / 'dist/zerolte')
    p.add_argument('--root-mode', choices=['rescue', 'userdata'], default='rescue')
    p.add_argument('--firmware-dir', type=Path, help='Required for userdata mode; never extracts firmware from a phone')
    p.add_argument('--busybox-archive', type=Path, help='Optional offline copy of the pinned upstream tarball')
    p.add_argument('--loader-source', type=Path, help='Optional clean checkout at the pinned uniLoader commit')
    p.add_argument('--kernel-image', type=Path, help='Reuse only the exact previously validated Image hash in the lock')
    a = p.parse_args()
    for name, expected in LOCK['integration_inputs'].items():
        require(sha((ROOT / name).read_bytes()) == expected, 'Changed integration input requires review/lock update: ' + name)
    for tool in ['git', 'make', 'clang', 'ld.lld', 'dtc', 'fdtput', 'aarch64-linux-gnu-gcc']:
        require(shutil.which(tool), 'Missing host tool: ' + tool)
    a.work = a.work.resolve()
    a.output = a.output.resolve()
    require(not a.output.exists(), 'Output already exists; choose a new directory')
    a.work.mkdir(parents=True, exist_ok=True)
    space(a.work)
    logs = a.work / ('run-' + str(time.time_ns()))
    logs.mkdir()
    run([sys.executable, ROOT / 'scripts/kernel.py', 'verify', a.kernel], logs / 'source.log')
    if a.kernel_image:
        image = a.kernel_image.resolve()
        require(sha(image.read_bytes()) == LOCK['kernel_validation']['Image_sha256'], 'Unrecognized cached Image')
    else:
        kout = logs / 'kernel'
        run([sys.executable, ROOT / 'scripts/kernel.py', 'build', a.kernel, kout], logs / 'kernel.log', seconds=2400)
        image = kout / 'arch/arm64/boot/Image'
    image64(image.read_bytes())
    dtb = logs / 'zerolte.dtb'
    run(['dtc', '-I', 'dts', '-O', 'dtb', '-o', dtb, ROOT / 'kernel/zerolte-system2.dts'], logs / 'dtc.log')
    firmware = {}
    if a.root_mode == 'rescue':
        # RAM rescue needs no proprietary firmware or radio initialization.
        for i, node in enumerate(['/soc@0/pcie@15660000', '/soc@0/serial@11460000/bluetooth']):
            run(['fdtput', '-t', 's', dtb, node, 'status', 'disabled'], logs / f'rescue-radio-{i}.log')
    else:
        require(a.firmware_dir is not None, 'userdata mode requires --firmware-dir; see docs/INSTALL.md')
        for name in ['brcm/brcmfmac4358-pcie.bin', 'brcm/brcmfmac4358-pcie.txt',
                     'brcm/BCM4358A3.samsung,exynos7420-zerolte.hcd', 'regulatory.db', 'regulatory.db.p7s']:
            path = a.firmware_dir / name
            require(path.is_file() and not path.is_symlink(), 'Missing regular firmware file: ' + name)
            data = path.read_bytes()
            if name.endswith('.txt'):
                require(b'macaddr=' not in data.lower(), 'Remove a device-specific macaddr from the NVRAM input before sharing')
            firmware['lib/firmware/' + name] = data
    archive = a.busybox_archive or a.work / 'busybox-1.37.0.tar.bz2'
    if not archive.exists():
        tmp = archive.with_suffix('.download')
        with urllib.request.urlopen(LOCK['busybox']['url'], timeout=60) as response, tmp.open('xb') as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                require(total <= 8 * 1024**2, 'BusyBox download exceeds expected bounds')
                output.write(chunk)
        require(sha(tmp.read_bytes()) == LOCK['busybox']['sha256'], 'BusyBox archive hash mismatch')
        tmp.rename(archive)
    require(sha(archive.read_bytes()) == LOCK['busybox']['sha256'], 'BusyBox archive hash mismatch')
    bsrc = logs / 'busybox-source'
    bsrc.mkdir()
    with tarfile.open(archive) as tar:
        tar.extractall(bsrc, filter='data')
    bsrc = bsrc / 'busybox-1.37.0'
    bout = logs / 'busybox'
    bout.mkdir()
    shutil.copyfile(ROOT / 'configs/busybox.config', bout / '.config')
    env = dict(os.environ, KCONFIG_NOTIMESTAMP='1')
    # BusyBox oldconfig's defaults are supplied from a complete pinned configuration.
    with (logs / 'busybox-config.log').open('wb') as output:
        subprocess.run(['make', '-C', str(bsrc), 'O=' + str(bout), 'CROSS_COMPILE=aarch64-linux-gnu-', 'oldconfig'],
                       input=b'\n' * 4096, stdout=output, stderr=subprocess.STDOUT, timeout=120, check=True, env=env)
    run(['make', '-C', bsrc, 'O=' + str(bout), 'CROSS_COMPILE=aarch64-linux-gnu-', '-j4'], logs / 'busybox-build.log')
    busybox = bout / 'busybox'
    elf = busybox.read_bytes()
    require(elf[:4] == b'\x7fELF' and int.from_bytes(elf[18:20], 'little') == 183, 'BusyBox is not AArch64')
    phoff = int.from_bytes(elf[32:40], 'little')
    phentsize = int.from_bytes(elf[54:56], 'little')
    phnum = int.from_bytes(elf[56:58], 'little')
    require(all(int.from_bytes(elf[phoff+i*phentsize:phoff+i*phentsize+4], 'little') != 3 for i in range(phnum)),
            'BusyBox must be statically linked')
    recovery = logs / 'reboot-recovery'
    run(['clang', '--target=aarch64-linux-gnu', '-fuse-ld=lld', '-nostdlib', '-static',
         '-Wl,-e,_start', ROOT / 'rescue/reboot-recovery.S', '-o', recovery], logs / 'recovery-helper.log')
    files = {'init': (ROOT / 'rescue/init.sh').read_bytes(),
             'sbin/s6-usb-setup': (ROOT / 'rescue/usb-setup.sh').read_bytes(),
             'sbin/reboot-recovery': recovery.read_bytes(), 'rescue/bin/busybox': elf,
             'etc/s6-root-mode': (a.root_mode + '\n').encode(), **firmware}
    dirs = {'dev', 'proc', 'sys', 'run', 'tmp', 'root', 'newroot', 'bin', 'sbin', 'etc', 'rescue', 'rescue/bin'}
    for name in files:
        dirs.update(str(parent) for parent in Path(name).parents if str(parent) != '.')
    entries = [(name, stat.S_IFDIR | 0o755, b'') for name in sorted(dirs, key=lambda n: (n.count('/'), n))]
    entries += [('bin/sh', stat.S_IFLNK | 0o777, b'/rescue/bin/busybox')]
    entries += [(name, stat.S_IFREG | (0o755 if name in ('init', 'sbin/s6-usb-setup', 'sbin/reboot-recovery', 'rescue/bin/busybox') else 0o644), data)
                for name, data in sorted(files.items())]
    initrd = logs / 'initramfs.cpio.gz'
    initrd.write_bytes(newc(entries))
    source = a.loader_source or a.work / 'uniloader-source'
    if not source.exists():
        source.mkdir()
        run(['git', 'init', source], logs / 'loader-git-init.log')
        run(['git', '-C', source, 'remote', 'add', 'origin', LOCK['uniloader']['url']], logs / 'loader-git-remote.log')
        run(['git', '-C', source, 'fetch', '--depth', '1', 'origin', LOCK['uniloader']['commit']], logs / 'loader-fetch.log')
        run(['git', '-C', source, 'checkout', '--detach', 'FETCH_HEAD'], logs / 'loader-checkout.log')
    require(git(source, 'rev-parse', 'HEAD') == LOCK['uniloader']['commit'], 'Wrong loader revision')
    require(not git(source, 'status', '--porcelain'), 'Loader source must be clean')
    uout = logs / 'uniloader'
    uout.mkdir()
    shutil.copyfile(ROOT / 'configs/uniloader.config', uout / '.config')
    # Reuse the already validated out-of-tree make interface; no upstream edits.
    for base, directories, _ in os.walk(source):
        directories[:] = [n for n in directories if n != '.git']
        for name in directories:
            (uout / (Path(base) / name).relative_to(source)).mkdir(parents=True, exist_ok=True)
    run(['make', '-B', '-C', source, 'O=' + str(uout), 'ARCH=aarch64', 'LLVM=1',
         'CPP=clang --target=aarch64-linux-gnu -E -Ulinux -Uunix',
         'KERNEL_PATH=' + str(image), 'DT_PATH=' + str(dtb), 'RAMDISK_PATH=' + str(initrd), '-j2'], logs / 'loader-build.log')
    image64((uout / 'uniLoader').read_bytes())
    a.output.mkdir(parents=True)
    for name, path in {'uniLoader': uout / 'uniLoader', 'Image': image, 'zerolte.dtb': dtb, 'initramfs.cpio.gz': initrd}.items():
        shutil.copyfile(path, a.output / name)
    manifest = {'schema': 1, 'model': 'SM-G925I', 'partition_bytes': CAPACITY, 'root_mode': a.root_mode,
                'kernel_source_tree': LOCK['kernel']['source_tree'], 'loader_commit': LOCK['uniloader']['commit'],
                'hardware_tested': False, 'userdata_installer': False,
                'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(a.output.iterdir())}}
    (a.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    load_bundle(a.output)
    (a.output / 'SHA256SUMS').write_text(''.join(f"{sha(path.read_bytes())}  {path.name}\n" for path in sorted(a.output.iterdir()) if path.name != 'SHA256SUMS'))
    print('Bundle ready:', a.output)
    print('BOOT is assembled locally by install.py from the owner\'s backed-up Samsung envelope.')
    print('Root mode:', a.root_mode, '; USERDATA is not installed or erased.')


if __name__ == '__main__':
    main()
