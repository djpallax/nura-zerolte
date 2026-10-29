# Source export checks — 2026-10-28

- Exported kernel patch matches the full SYSTEM2 source delta previously recorded
  during hardware validation. No untracked source files were present in that tree.
- Applied Git's cached patch check against a temporary index populated from the
  exact upstream base. The active checkout and its index were not changed.
- Decompiled SYSTEM2 DTB compiles with dtc. Model, bootargs and poweroff mask/value
  properties match the tested DTB after roundtrip. This is not a native DTS cleanup
  or a validation of every dtc warning/binding.
- Selected Python sources parse successfully; selected shell scripts pass sh -n.
- Public-tree preflight passes. An additional local-only comparison found none of
  the known development root/mobile passwords, SSIDs, serial, host path, LAN address
  or filesystem UUID in this export. No secret values are included in this report.
- No phone access, partition write, rootfs extraction, GitHub push or remote
  repository creation was performed for this export.

Not yet checked: a full kernel rebuild using the new wrapper from a clean clone,
complete loader/initramfs/BOOT regeneration, clean rootfs build, package ownership
and licensing review, recovery installer and end-to-end installation. The checks
above establish source capture and basic reconstruction only. Existing hardware
results apply to the local SYSTEM2 image; they do not certify a future rebuild.
