# BOOT packaging and TWRP installation

The implemented flow is documented step by step in [INSTALL.md](INSTALL.md).
Run scripts/build.py for the kernel, clean initramfs and pinned uniLoader bundle,
then scripts/install.py check/install with the phone in TWRP.

The installer backs up the owner's BOOT and preserves its Samsung header,
outer ramdisk, DT tables and opaque footer. Only the loader payload and the
corresponding header size/checksum are replaced. It refuses unfamiliar header
addresses/page layout or a result larger than the verified 28 MiB BOOT target.
The resulting boot.img stays in private/backups, not in the source repository.

A complete pushed-image hash is checked before writing; the entire partition is
read back afterward. RECOVERY is hashed before and after. A failed/uncertain
write stops without reboot or automatic repeat. Restore uses the original
per-device receipt and verifies backup integrity before one guarded write.

USERDATA installation is separate and remains unimplemented. This pipeline
never writes RECOVERY, SYSTEM, EFS, modem or the partition table. The initramfs
is RAM-only by default. See INSTALL.md for the explicitly selected existing-Nura
root handoff, firmware inputs and limits of offline validation.
