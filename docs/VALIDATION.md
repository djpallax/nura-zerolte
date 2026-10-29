# Cleaned source preparation validation

Updated 2026-10-29. The integration snapshot uses the cleaned publication kernel,
replacing the initial diagnostic-heavy SYSTEM2 patch.

The fork's prepared tree is pinned in sources.lock.json. Complete ARM64 Image
compilation passed with CONFIG_WERROR=y and upstream's standard warnings; all
22 modified C objects also passed W=1. The defconfig reproduced the full config
byte-for-byte. Binding and implementation patch drafts passed checkpatch
separately. The cleaned candidate still needs hardware regression testing;
previous development results are identified in HARDWARE.md.

The wrapper accepts either a clean committed tree matching the lock or an exact
application of the fallback patch onto its upstream base. The kernel/rescue bundle and BOOT installer now exist; a first-time pmOS
rootfs pipeline is still missing. No phone data was extracted for this preparation.
See INITIAL-EXPORT-VALIDATION.md for the historical capture checks.

## Clean bundle and installer validation

A real RAM-rescue bundle was built from the validated Image, the pinned static
BusyBox source tarball, the unchanged pinned loader and new credential-free init.
The installer tests use synthetic BOOT and fake ADB; no test flashes a phone.
They cover Samsung envelope preservation, backup/restore, model rejection,
corrupt bundle/push, failed writes/readback and refusal to reboot/retry failures.
A read-only real-device preflight was attempted, but no ADB/recovery or matching
USB device was present. No real partition write or reboot was performed. The new
clean initramfs and assembled BOOT are not claimed hardware-validated.
