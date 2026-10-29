# How Nura/postmarketOS was installed on this port

The installation procedure is known and was performed on the development phone.
What remains unfinished is its conversion into a clean, general-purpose rootfs
builder/installer. This document records the actual stages, inputs and system
integration rather than treating the installed phone as an undocumented image.

**Scope:** SM-G925I, Linux 7.2.12, Nura/postmarketOS v26.06, OpenRC, a persistent
ext4 root on USERDATA, and subsequently Plasma Mobile 6.6.6 with Panfrost.
No partition table changes or installation into SYSTEM were used.

The command blocks below reconstruct equivalent operations from retained scripts,
package databases and validation logs. They are not claimed to be a verbatim shell
history or a currently tested one-command rootfs installer. Nothing in this
procedure authorizes erasing another owner's data without their explicit choice.

## 1. Establish a working RAM rescue system first

We first booted an Alpine ARM64 userspace entirely from initramfs and verified
BusyBox USB serial, USB networking, key-authenticated SSH, OpenRC, APK database
transactions and the UFS driver. This gave us a running environment independent
of the filesystem we were about to replace.

The first persistent-root installation was streamed **over SSH from that Linux
RAM rescue system**, not through the current BOOT-only ADB installer. TWRP was
used for device inspection, BOOT backups/flashing and subsequent recovery tests.
A working RAM rescue and a working UFS write/readback test preceded replacement.

## 2. Build a fresh ARM64 root on the host

### Recorded inputs

| Input | Recorded version |
| --- | --- |
| Alpine minirootfs | 3.24.3, aarch64 |
| Nura/pmOS branch | v26.06 |
| postmarketos-base / postmarketos-base-openrc | 62-r0 |
| postmarketos-release | 62-r0 |
| postmarketos-keys | 1-r1 |
| OpenRC | 0.63.2-r0 |
| APK tools | 3.0.8-r0 |
| musl | 1.2.6-r3 |

The initial root's full package/version list is in
[PMOS-BASE-PACKAGES.txt](PMOS-BASE-PACKAGES.txt). Checksums of the minirootfs and
public key package are also recorded in sources.lock.json.

Recorded repository configuration:

```text
https://dl-cdn.alpinelinux.org/alpine/v3.24/main
https://dl-cdn.alpinelinux.org/alpine/v3.24/community
https://mirror.postmarketos.org/postmarketos/v26.06
```

These are the historical release inputs, not an instruction to mix an arbitrary
current Alpine edge branch into v26.06. Repository availability/package revisions
can change; a complete repeatable builder must preserve the corresponding signed
indexes and dependency packages or pin equivalent verified inputs deliberately.

A host-side staging outline is:

```sh
S6_ROOTFS="$PWD/build/pmos-rootfs"
mkdir -p "$S6_ROOTFS" build/downloads

curl -fL -o build/downloads/alpine-minirootfs.tar.gz \
  https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/aarch64/alpine-minirootfs-3.24.3-aarch64.tar.gz
printf '%s  %s\n' \
  4d3f80afaebd447c5591a63a73bde380a149fe8b2d85488cafabb2ff97551f50 \
  build/downloads/alpine-minirootfs.tar.gz | sha256sum -c -

tar -xpf build/downloads/alpine-minirootfs.tar.gz -C "$S6_ROOTFS"
```

The development minirootfs also passed detached GPG signature verification with
Alpine release key fingerprint
`0482D84022F52DF1C4E7CD43293ACD0907D9495A`. Independently verify the trusted
upstream key when reproducing the signature check; a matching downloaded key
name alone is not a trust anchor.

### Public signing keys and package installation

We added the official pmOS public APK signing key and retained signature checking.
The recorded public-key package was postmarketos-keys-1-r1.apk, SHA256:

```text
91302c92afa6c45aed211be483e25652d9a4df8808a17c92f227773b38871210
```

It contains etc/apk/keys/build.postmarketos.org.rsa.pub. This is a public package
signing key, not an SSH host private key. A reconstruction can fetch that exact
package, verify its recorded hash, and extract only its public key into the
staging root before using the repository:

```sh
curl -fL -o build/downloads/postmarketos-keys.apk \
  https://mirror.postmarketos.org/postmarketos/v26.06/aarch64/postmarketos-keys-1-r1.apk
printf '%s  %s\n' \
  91302c92afa6c45aed211be483e25652d9a4df8808a17c92f227773b38871210 \
  build/downloads/postmarketos-keys.apk | sha256sum -c -
tar --ignore-zeros -xzpf build/downloads/postmarketos-keys.apk \
  -C "$S6_ROOTFS" --wildcards 'etc/apk/keys/*'
```

Configure the three repositories above in the staging root. On an x86_64 host,
use AArch64 emulation or a native aarch64 build environment for its APK executable.
For example, with qemu-user-static installed, a temporary host qemu-aarch64-static
inside the staging root can run `/sbin/apk` through chroot. This is a reconstruction
method; the temporary host emulator must be removed before packaging.

The initial explicit world package set was:

```text
alpine-baselayout alpine-keys alpine-release apk-tools busybox musl-utils
openrc postmarketos-base postmarketos-base-openrc
```

Equivalent package transaction inside that staging environment:

```sh
apk --no-scripts --no-commit-hooks add \
  alpine-baselayout alpine-keys alpine-release apk-tools busybox musl-utils \
  openrc postmarketos-base=62-r0 postmarketos-base-openrc=62-r0
```

This installs actual Nura/pmOS base packages; it is not merely a renamed Alpine
motd. An unknown package signature caused a later GUI transaction to stop; we
used the compatible signed Alpine repository rather than allow-untrusted.
Package scripts/commit hooks were intentionally disabled because this port has a
custom boot pipeline: generic initramfs/boot-deploy hooks must not rewrite BOOT.
Necessary accounts, services and caches were then completed explicitly.

## 3. Add the board-specific persistent-root integration

The host preparer added the following to the clean root before archiving it:

| Destination | What was installed |
| --- | --- |
| /rescue/bin/busybox | Static rescue BusyBox independent of the distro libc. |
| /sbin/reboot-recovery | The validated AArch64 RESTART2 recovery helper. |
| /sbin/s6-persistent-init | Filesystem setup, USB rescue supervision and distro init handoff. |
| /sbin/ramroot1-usb-setup | The initial ACM/ECM gadget configuration. |
| /etc/inittab | BusyBox PID1 invokes OpenRC sysinit, boot, default and shutdown. |
| /etc/init.d/ramroot1-ssh | Key-only SSH restricted to the USB interface address. |
| /etc/rc.conf | Serial OpenRC startup, no unsupported cgroup controller setup. |
| /etc/fstab | No automatic mount of other phone partitions. |
| /etc/s6-install-id | A newly generated S6-NURA- installation marker. |
| /etc/s6-build-epoch | Initial clock fallback; not RTC support. |
| /etc/s6-rootfs.sha256 | Per-file verification of the staged payload. |

The source templates now included under userspace/ are
s6-persistent-init.sh, s6-ramroot1.inittab, s6-ramroot1-usb-setup.sh and
s6-ramroot1-ssh.openrc. The persistent init mounts volatile /run and /tmp,
keeps the CONSOLEFIX1 USB shell respawn loop independent of OpenRC, and finishes
with exec /sbin/init. The USB gadget is configured once, without resetting DWC3.

The first private development payload reused our existing static Dropbear,
firmware and owner-authorized SSH material. That reuse is **not** a public-image
recipe. A portable image must build/install its own SSH executable, generate host
keys on first boot and accept only its new owner's authorized key. The initial
service expects /sbin/dropbear; adjust that path if using the distro package.
No host private keys, owner authorized_keys or network profiles are in this repo.

Initially only the USB SSH service was enabled in the default runlevel. GUI and
Wi-Fi services were added after persistent boot and drivers were demonstrated.
The archive used root UID/GID metadata and preserved file modes/symlinks; file
hashes were checked again on the phone. The staging root was not copied from an
existing Android system or from a complete personalized phone installation.

## 4. Replace only USERDATA filesystem contents

On the tested phone, USERDATA was the ext4 partition exposed as /dev/sda18.
That is a historical observation, not a portable target-selection rule. Its
actual PARTNAME, device identity, geometry and existing filesystem were checked
before writing. The owner explicitly waived a content backup for that test
partition; that waiver does not apply to another owner or installation.

The original installer performed these operations in order:

1. Verify the running RAM rescue, Samsung storage identity and the exact intended
   USERDATA partition. Require it to be unmounted and other protected partitions
   read-only. Verify the rootfs archive hash on the host.
2. Enable writes only as needed for USERDATA and mount its existing ext4 at a
   dedicated installation mountpoint. Verify the exact mount and absence of
   nested mounted filesystems. Check that the prior content is the authorized
   disposable Nura test installation.
3. Remove that filesystem's old top-level entries except lost+found. No mkfs or
   partition table rewrite was used: ext4, its identity and geometry survived.
4. Stream the verified tar.gz from the host over SSH into the RAM-resident
   installer; extract into the verified USERDATA mount with ownership/modes.
5. Run sha256sum -c etc/s6-rootfs.sha256 over the payload. Check /etc/os-release,
   the persistent init, OpenRC and the installed pmOS base packages in chroot.
6. Sync, unmount USERDATA and restore read-only block protection. Keep the RAM
   rescue BOOT until the separate persistent-root boot candidate is verified.

The transport shape was a host SSH command with the archive on standard input,
not a raw dd of a full-disk image. The destructive filesystem selection/deletion
was inside a separately uploaded, guarded RAM installer. Original development
script names were s6-nura-root-prepare.py, s6-nura-install.py and
s6-nura-install-device.sh. They were tied to that installation's geometry,
identity and consent, so copying them unchanged is not a portable installer.

The post-extraction checks included:

```sh
# Inside the verified USERDATA mount, before unmounting it:
sha256sum -c etc/s6-rootfs.sha256
chroot . /bin/sh -c 'cat /etc/os-release; /sbin/openrc --version'
chroot . /sbin/apk --network=no info -e postmarketos-base postmarketos-base-openrc
```

Those are verification operations, not authorization to mount/erase an arbitrary
partition. This document deliberately does not turn an old owner-specific erase
command into a copy-and-paste installation command for an unknown phone.

## 5. Switch from RAM rescue to the persistent root

The original initramfs selected USERDATA by its verified partition metadata,
filesystem identity and installation marker, mounted it and moved /dev, /proc
and /sys before switch_root into /sbin/s6-persistent-init. A complete Alpine RAM
fallback remained available if selection failed. A successful chroot was not
counted as a successful persistent boot.

Early iterations exposed UFS shutdown ordering and MAX77843 interrupt/I2C probe
problems. Kernel fixes and recovery testing came before a later image demonstrated
persistent boot. The successful installation was kept while BOOT was iterated;
USERDATA was not reinstalled for every kernel attempt.

The current public bundle differs deliberately: it defaults to a smaller clean
BusyBox RAM rescue. Its explicit --root-mode userdata checks the generic port
marker and Nura identity instead of embedding the original owner's filesystem
UUID. It requires the matching firmware inputs. See INSTALL.md for that handoff.

## 6. Add the desktop and radio integration incrementally

We first installed signed Xorg/fbdev, Openbox, xterm, libinput and evtest packages
to verify display/touch. Then we installed a minimal Plasma Mobile/KWin session.
The initial Plasma session used software rendering over the earlier display;
DRM/simpledrm plus Panfrost later enabled the direct native Wayland session.

The primary desktop packages were plasma-mobile, kwin, Mesa Gallium, Breeze,
plasma-settings, qmlkonsole, plasma-keyboard and Xwayland. Auxiliary tools included
swayidle, kscreen-doctor, pulseaudio-utils and kdialog. Names/versions should be
resolved against the pinned release repositories rather than a rolling branch.

The mobile account was created with its own home and input/video/render access
as required by actual device ownership. D-Bus and udev were started, the input
and DRM devices were initialized in udev, and font/MIME/GLib caches were generated
explicitly after the no-scripts package transactions.

The native session sources are now included:

| Source under userspace/ | Installed role |
| --- | --- |
| s6-plasma-native.openrc | /etc/init.d/s6-plasma-native service. |
| s6-plasma-native-session.sh | /usr/local/bin/s6-plasma-native-session. |
| s6-system1-native-shell.sh | The shell launched as /usr/local/bin/s6-plasma-native-shell. |
| s6-kwin-drm-nonblock.c | /usr/local/lib/s6-kwin-drm-nonblock.so, built for target musl. |
| s6-vt-mode.c | /usr/local/sbin/s6-vt-mode, built for target userspace. |

The KWin helper adds O_NONBLOCK only to its DRM device open and removes
LD_PRELOAD from child environments. It worked around the observed NoopSession
DRM event-read stall; it is not a generic substitute for session management.
Build these target helpers with the target musl toolchain, or natively on Alpine;
do not copy a glibc-linked host library into the phone's musl userspace.

The session uses KWin's DRM backend, Mesa/Panfrost GLES, plasma-keyboard and a
3x output scale. It changes to the mobile home before launching, exports its
Wayland environment to D-Bus, and keeps logs/caches/history under /run. The old
software/Xorg session was retained as a rollback, not used as proof of GPU support.

Later we installed NetworkManager, BlueZ, plasma-nm, bluedevil and polkit. Only
wlan0 is managed; the USB rescue path remains independent. A udev network
preflight, radio-only policy and serialized SSH-listener dispatcher completed
the integration. We corrected the messagebus service account's primary group
and polkit account/directory ownership rather than granting global policy access.
Each new owner supplies their own Wi-Fi settings; no saved profile is reused.

Finally we added the physical-button listener, key backlight interface, idle
screen handling, fixed-command power broker, sudo and fastfetch. Root/mobile
passwords are distinct and owner-provisioned; password SSH remains disabled.
Package installation alone does not implement these custom service/configuration
steps. The selected scripts are present in userspace/ for packaging and review.

## 7. What was verified, and what remains to automate

Persistent-root boot, marker persistence, BOOT readback, recovery roundtrips,
USB rescue, wireless SSH, Plasma/Panfrost and physical touch/keyboard were
verified during development. See HARDWARE.md for limitations. The new public
clean bundle has compile/offline tests but no new physical boot qualification.

Remaining work is concrete: package this configuration into proper device/kernel
and service APKBUILDs, preserve complete dependency inputs, provision fresh
identities on first boot, and replace the owner-specific historical USERDATA
installer with an explicitly authorized general installer and rollback path.
The current scripts/install.py is intentionally BOOT-only; it must not be
represented as already performing this initial distribution installation.
