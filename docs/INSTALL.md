# Build and install the kernel through TWRP

Experimental support for **SM-G925I only**. This workflow installs a kernel,
matching device tree, loader and clean rescue initramfs into BOOT. It does not
install a distribution, format USERDATA or write RECOVERY/SYSTEM/EFS/modem.

## Choose the workflow

| Starting point | Workflow |
| --- | --- |
| First time testing the port | Build and boot RAM rescue. Confirm USB serial and storage detection before considering any rootfs changes. |
| Existing Nura installation on USERDATA | Build a userdata bundle with the five firmware inputs and install it through TWRP. |
| Android or a blank USERDATA partition | Boot RAM rescue first, then follow the provisioning prerequisites in [PMOS.md](PMOS.md). The BOOT installer alone cannot complete this path. |

## 1. Host requirements and source clones

Use a Linux host with Python 3.12+, Clang/LLD, AArch64 GCC, GNU make, dtc and ADB.
Keep at least
12 GiB free throughout compilation. Typical Debian/Ubuntu prerequisites:

```sh
sudo apt install git python3 build-essential clang lld llvm \
  gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu device-tree-compiler \
  flex bison libssl-dev libelf-dev bc bzip2 cpio picocom adb

git clone https://github.com/djpallax/nura-zerolte.git

git clone --depth 1 --single-branch --branch zerolte-7.2.12 \
  https://github.com/djpallax/linux-zerolte.git
cd nura-zerolte
```

The kernel helper verifies the tree recorded in `sources.lock.json`. If the
fork branch has a different tree, use the pinned upstream tag and bundled patch:

```sh
git clone --depth 1 --branch v7.2.12 \
  https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable.git \
  ../linux-zerolte-fallback
python3 scripts/kernel.py prepare ../linux-zerolte-fallback
python3 scripts/build.py --kernel ../linux-zerolte-fallback
```

The last command replaces the standard build command in step 2. Use a new
`--output` path for a retry. If using the Arm GNU toolchain instead of the distro
cross compiler, add its `bin` directory to PATH and export
`NURA_TOOLCHAIN_PREFIX=aarch64-none-linux-gnu-`.

## 2. Build the kernel and clean boot bundle

```sh
python3 scripts/build.py --kernel ../linux-zerolte
```

This compiles the kernel, device tree, static BusyBox, recovery helper and
uniLoader. BusyBox and uniLoader are fetched automatically at the revision/hash
in sources.lock.json; they are not extra manual clone steps. Upstream loader
code is used unchanged through its existing build interface. Build logs and
sources stay in build/; results go to dist/zerolte/.

The output contains Image, DTB, initramfs, loader, manifest and SHA256SUMS.
Default mode is **RAM rescue**: no rootfs is mounted, firmware is not needed,
Wi-Fi/Bluetooth DT nodes are disabled, and a respawned USB BusyBox shell is
provided. There is no SSH server or copied identity in the rescue image.
The USB root shell is intended for a physically connected development device.

The bundle is not a generic Android boot.img. Samsung outer boot metadata/DT
tables are preserved from the owner's BOOT by the installer, locally. This avoids
distributing another person's BOOT backup or proprietary outer data in the repo.

## 3. Connect TWRP and run a no-write preflight

Boot the phone into TWRP and connect it over USB. Verify that ADB can access it:

```sh
adb devices -l
adb shell id
python3 scripts/install.py check
```

One device must appear in state recovery, with a root shell and TWRP version.
The development phone uses TWRP 3.2.3-0.
If several ADB devices are present, pass --serial YOUR_DEVICE to check/install.
If permissions fail, fix the host's normal ADB/udev access; do not disable access
protections. Automatic Linux boot monitoring also needs ordinary read/write
access to /dev/ttyACM devices (typically the dialout group on Debian/Ubuntu). Linux itself uses CDC ACM, so ADB absence there is expected.

The check validates model/codename, BOOT target/size, bundle hashes and a real
shell nonce. It saves BOOT twice and checks both copies agree, hashes RECOVERY,
and constructs a candidate in a private local backup directory. It writes no
phone partition and does not reboot. Backups/receipts are under private/backups/
and must never be committed or shared: old BOOT images can contain private data.

## 4. Install once and optionally reboot

```sh
python3 scripts/install.py install --reboot
```

The installer repeats preflight, keeps a fresh local backup, pushes the candidate,
checks its device-side hash, writes **only BOOT once**, reads the entire partition
back, and checks that RECOVERY's hash is unchanged. Only then is reboot sent.
Omit --reboot to leave the phone in TWRP after installation.

With --reboot it correlates the original USB port with the Linux 0525:a4a7 gadget
and requires a real nonce reply over CDC ACM within 180 seconds. No DWC3 reset,
controller unbind/bind, repeat flash or automatic rollback is attempted. If the
write/readback fails, it stops without rebooting. If boot does not respond,
return to TWRP and use the saved receipt to restore.

The default rescue mode does not start Plasma. It tests the kernel/USB rescue
path without replacing Android or another OS's filesystem. Kernel-only BOOT
replacement changes what boots normally; the original BOOT backup is essential.
From TWRP you can also reboot manually with `adb reboot system` after an
install without `--reboot`. Wait for the Linux gadget, then open the console
with `picocom -b 115200 /dev/ttyACM0`. From Nura or RAM rescue,
`/sbin/reboot-recovery` returns to TWRP. The development phone can take tens
of seconds to enumerate over USB.

## 5. Restore the original BOOT

Return to TWRP, then use the receipt path printed during installation:

```sh
python3 scripts/install.py restore \
  --receipt private/backups/YOUR_INSTALL_RUN/receipt.json --reboot
```

The script checks the backup hash, same phone serial/model and partition capacity,
backs up the current BOOT, restores once and verifies full readback. The original
OS need not provide CDC ACM, so restore does not claim a Linux console check.
An unresolved previous write blocks another install until inspected/restored.

## Existing compatible Nura root: advanced kernel update

This is not a first-time Nura installer. If the phone already has the matching
Nura USERDATA layout, provide locally obtained, legally usable firmware under a
lib/firmware-style directory with these files. They are needed in the
initramfs because the built-in drivers probe before USERDATA is mounted.

- brcm/brcmfmac4358-pcie.bin
- brcm/brcmfmac4358-pcie.txt
- brcm/BCM4358A3.samsung,exynos7420-zerolte.hcd
- regulatory.db and regulatory.db.p7s

Do not share personal NVRAM MAC identities. The builder rejects a macaddr= entry
in the NVRAM input; sanitize that input before redistribution. No Wi-Fi network
profiles, passwords or SSH keys are required. Use regular, nonempty files in
the expected paths. If the firmware source uses compressed blobs or symlinks,
copy the decompressed contents into your private firmware directory.

```sh
python3 scripts/build.py --kernel ../linux-zerolte \
  --root-mode userdata --firmware-dir /path/to/firmware \
  --output dist/zerolte-userdata
python3 scripts/install.py check --bundle dist/zerolte-userdata
python3 scripts/install.py install --bundle dist/zerolte-userdata --reboot
```

The initramfs first inspects USERDATA read-only without journal replay. It hands
off only when the existing port's installation marker, Nura/pmOS identity and
persistent init/rescue paths match. It then reopens the filesystem normally RW
for the existing OS to boot. Other layouts fall back to RAM rescue. It never
formats, extracts a rootfs or migrates an unknown installation automatically.
First-time clean Nura installation remains the separate work described in PMOS.md.

## Validation and offline tests

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Tests use a fake ADB executable and synthetic BOOT images; they never access a
phone. They cover preservation of Samsung outer components/footer, backup and
restore, wrong-model rejection, tampered bundles, failed push/write/readback,
no reboot on failure and refusal to retry an uncertain write. A real bundle
can be verified with `sha256sum -c SHA256SUMS` from its output directory.
