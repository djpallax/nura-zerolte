# Kernel build

For the complete build-and-install workflow, use [INSTALL.md](INSTALL.md).
The kernel.py commands below are lower-level kernel-only operations.

First commit and push the reviewed fork to djpallax/linux-zerolte, branch
zerolte-7.2.12. Do not apply the fallback patch to that branch again.

## Build from the fork

From this integration repository directory, once the kernel branch is available:

```sh
git clone --depth 1 --single-branch --branch zerolte-7.2.12 \
  https://github.com/djpallax/linux-zerolte.git ../linux-zerolte-build
python3 scripts/kernel.py build ../linux-zerolte-build ../build-zerolte
```

Choose new names if those directories exist. The output must be outside the
source tree and must not exist when the wrapper starts. The wrapper checks the
clean fork's Git tree against sources.lock.json and rejects different/modified
source. A newer revision needs an intentional lock update and fresh validation.

Dependencies: Python 3, Git, GNU make, Clang/LLD, dtc, flex, bison and standard
kernel host development packages. Validation used Clang/LLD 18.1.3. The wrapper
uses four jobs, enforces 12 GiB free space and builds Image plus the supplied
DTS. Decompiled DTS warnings/bindings are not claimed resolved. It does not
produce BOOT, a TWRP ZIP or a rootfs.

The fork also provides arch/arm64/configs/zerolte_defconfig for manual builds:

```sh
make -C ../linux-zerolte-build O="$PWD/../build-zerolte-manual" \
  ARCH=arm64 LLVM=1 zerolte_defconfig
make -C ../linux-zerolte-build O="$PWD/../build-zerolte-manual" \
  ARCH=arm64 LLVM=1 -j4 Image
```

## Fallback before the fork commit is available

```sh
git clone --depth 1 --single-branch --branch v7.2.12 --origin upstream \
  https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable.git \
  ../linux-zerolte-fallback
python3 scripts/kernel.py check ../linux-zerolte-fallback
python3 scripts/kernel.py prepare ../linux-zerolte-fallback
python3 scripts/kernel.py build ../linux-zerolte-fallback ../build-zerolte-fallback
```

Preparation requires clean upstream commit
cc9de5d4b5ab6459f5774946aa3195ad51236fa8 and applies the patch with --index.
Never run preparation over personal modifications.

Source/config identity is pinned. Byte-identical artifacts also require pinned
toolchain, build user/host/time/version and every firmware/initramfs input; those
full release constraints are not implemented. Hardware results still belong to
earlier development images, not a new regression test of the cleaned candidate.
