# nura-zerolte

Independent integration project for Nura/postmarketOS on the Samsung Galaxy S6
Edge **SM-G925I (zerolte)**, Exynos7420, 3 GB RAM. Not an official Nura port.
Other variants have not been tested.

| Repository | Contents |
| --- | --- |
| `djpallax/linux-zerolte` | Kernel drivers, bindings, defconfig and hardware notes. |
| `djpallax/nura-zerolte` | Instructions, source locks, integration sources and future image/installer recipes. |

The cleaned kernel builds with Clang/LLD 18.1.3 and CONFIG_WERROR=y; all 22 modified
C objects also passed W=1. Earlier development images booted Plasma Mobile with
touch, GPU acceleration, Wi-Fi and Bluetooth. See [hardware status](docs/HARDWARE.md).

**Kernel/rescue bundle building and a BOOT-only TWRP installer are available.**
A first-time Nura rootfs installer is not implemented yet. The new clean boot
bundle still needs physical regression testing; this is an experimental port.

## Build and install

```sh
git clone https://github.com/djpallax/nura-zerolte.git
git clone --depth 1 --single-branch --branch zerolte-7.2.12 \
  https://github.com/djpallax/linux-zerolte.git
cd nura-zerolte
python3 scripts/build.py --kernel ../linux-zerolte

# Connect the SM-G925I in TWRP with working ADB access.
adb devices -l
python3 scripts/install.py check
python3 scripts/install.py install --reboot
```

Read [INSTALL.md](docs/INSTALL.md) first for dependencies, backups, rollback and
firmware requirements. The default image boots a clean USB BusyBox rescue in RAM;
it does not install pmOS or erase USERDATA. Existing compatible Nura installations
have a separate, explicit userdata boot mode. The installer writes BOOT only,
verifies full readback and keeps the original BOOT in a private local directory.

See [kernel details](docs/KERNEL.md), [boot packaging](docs/BOOT.md),
[pmOS integration](docs/PMOS.md) and [GitHub setup](docs/GITHUB.md).

```sh
python3 scripts/check-public-tree.py
sha256sum -c SOURCE-SHA256SUMS
```

sources.lock.json records the upstream base, cleaned Git tree identity, patch and
config hashes, and the last locally built Image hash. The fork commit stays null
until it has been committed/pushed; no commit hash has been invented. The tree
identity verifies the source snapshot even after a shallow clone of the fork.

kernel/zerolte.patch is a fallback against upstream v7.2.12. Do not apply it again
to the patched fork. kernel/zerolte-system2.dts is decompiled development DT data;
native kernel DTS integration and binding validation remain necessary.
userspace/ contains selected inputs, not a complete installed device package.

## Privacy, licensing and provenance

No phone rootfs, BOOT backups, Wi-Fi profiles, passwords or SSH identities are
included. Generate credentials and identities per installation. The checker is
a limited preflight, not a complete secret/license audit.

Kernel changes preserve upstream licensing/attribution. Licensing and provenance
review of integration sources and firmware remains a release task; this export
does not assign a replacement blanket license.

This independent experiment has substantial AI assistance. See the [Nura policy
notes](docs/NURA.md), [validation](docs/VALIDATION.md) and [release plan](docs/RELEASE-PLAN.md).
