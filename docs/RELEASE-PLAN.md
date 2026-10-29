# From development snapshot to a reproducible release

Update: kernel/rescue bundle generation and a guarded BOOT-only ADB installer
are now implemented in scripts/build.py and scripts/install.py. See INSTALL.md.
The milestones below retain the broader full-OS release plan; clean pmOS rootfs
packaging, a TWRP UI ZIP and physical regression tests remain pending.

## Repository layout

Use djpallax/nura-zerolte for integration, recipes, scripts, status and releases.
A separate kernel fork (for example linux-zerolte) is useful for long-term driver
work and reviewable commits. It is optional initially: sources.lock.json plus
kernel/zerolte.patch pins the same source state without uploading kernel history.
Keep original upstream as upstream, personal fork as origin, and use a branch
such as zerolte-7.2.12. Do not fork the vendor 3.10 kernel as the base of this
mainline port. Preserve licenses and source provenance when splitting commits.

## 1. Source capture (prepared)

The export contains the cleaned tracked kernel delta, tested configuration,
decompiled SYSTEM2 DTS, and selected non-personal integration sources. Verify the
patch against its base and convert the DTS modifications into maintained source
files with labels/bindings. Current exported helpers are inputs, not an installed
device package. Audit hard-coded UID 1000, paths and service dependencies.

## 2. Clean rootfs recipe (required)

Build Nura/postmarketOS from signed repositories through a pinned pmbootstrap and
pmaports revision. Pin repository branch, package versions and source checksums.
Package custom services instead of replaying interactive apk/manual account fixes.
Include Plasma Mobile, NetworkManager, BlueZ, sudo and fastfetch as selectable
packages; support a smaller SSH-only image. Preserve OpenRC until another init is
explicitly ported and tested. Do not transplant the installed phone filesystem.

Generate root/mobile passwords or prompt during provisioning; never ship the
development passwords/hashes. Generate SSH host keys, machine-id and radio MAC
identity per installation. Wi-Fi setup belongs to the end user. Do not ship
authorized_keys, NetworkManager profiles, wpa_supplicant configurations, shell
history, crash dumps, user caches, installation UUIDs or phone serial numbers.
The old local rootfs preparer copies private SSH host material and is deliberately
excluded. Existing BOOT/initramfs may also embed SSH credentials and must be rebuilt.

## 3. BOOT build (required)

Pin loader revision, toolchain and build settings. Build kernel, DTB, clean
initramfs, then uniLoader through its existing build interface. Generate the
Android boot header from documented model parameters, not from a private prior
image. Check component hashes, embedded content, header/page layout and the actual
BOOT capacity; retain verified rescue and readback backups locally. Audit firmware
licenses before redistributing blobs; otherwise provide extraction with checksums.

## 4. Two installation outputs (required)

Produce a BOOT image, clean rootfs archive/image, manifest and SHA256SUMS as release
assets. Source repositories contain recipes, not multi-gigabyte build iterations.

ADB path: require exactly one explicitly selected TWRP device, verify its model
and actual by-name targets/sizes, back up BOOT, push verified payload, write BOOT
only and compare full readback. USERDATA installation is a separate explicit
destructive action with local backup choice. Do not hard-code our filesystem UUID.

TWRP path: use a compatible recovery installer with the same checks. State clearly
whether it writes BOOT only or also replaces USERDATA. Preserve RECOVERY, SYSTEM,
EFS, modem and the partition table. Offer BOOT restore from the user's own backup.
Do not execute old stage hardware scripts against another owner's phone.

## 5. Clean-room verification and release (required)

Rebuild from a fresh checkout without out/, evidence/, existing BOOT images or
the test phone. Verify source versions, package signatures, archive metadata,
absence of credentials, and deterministic outputs where supported. Exercise
installer refusal on wrong model, size/hash mismatch and missing backups before
an authorized device install. Then confirm boot, USB rescue, thermal protection,
rootfs persistence, radios/SSH and GUI. Publish an experimental status matrix and
per-artifact hashes; do not claim stability from a successful compilation.

## GitHub sequence

Only initialize Git in this export directory after review; the workspace root
contains private backups and is not the publication root. Choose licensing after
reviewing existing copyrights. Run scripts/check-public-tree.py before every
release, review the exact staged diff, then create djpallax/nura-zerolte. Do not
upload the workspace .git placeholder, out/, evidence/ or phone-derived archives.
No GitHub repository was created by this preparation.
