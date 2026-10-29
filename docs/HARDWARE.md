# Hardware status

The table describes previous SYSTEM2 development hardware results. The cleaned
publication kernel is compile-validated and still needs hardware regression
testing. Kernel source is maintained in djpallax/linux-zerolte.


“Working” means observed on the development hardware with the required external
configuration/firmware. It is not a promise that the kernel alone enables the
feature, or that every power state and error path has been qualified.

| Feature | Status | Evidence and limitations |
| --- | --- | --- |
| Boot to Linux | Working | Requires the matching DTB, initramfs and loader; cleanup still needs hardware regression testing. |
| USB serial rescue console | Working | CDC ACM in Linux; ADB is provided by TWRP, not this Linux gadget. |
| USB networking and SSH | Working | Requires gadget and SSH userspace configuration. |
| UFS and persistent root filesystem | Working | USERDATA/ext4 tested; recovery roundtrips observed. |
| Four Cortex-A53 + four Cortex-A57 CPUs | Working with thermal limits | All eight brought online; thermal policy can park six cores. |
| CPU frequency scaling | Working with limits | Bounded transitions tested; full ASV tuning and sustained-load qualification remain. |
| Cross-CPU timekeeping | Working in tested configuration | Physical-counter workaround; direct vDSO counter reads disabled. |
| Battery and charger temperatures | Working | ADC/NTC measurements with board-specific tables. |
| SoC temperature and automatic cooling | Working with limits | TMU monitoring, frequency caps and core parking observed; this is not complete hardware-trip qualification. |
| Battery percentage/voltage/current | Working | Read-only telemetry; depends on inherited fuel-gauge state. |
| Active charging control | Not implemented | Firmware settings are preserved; telemetry is not charger management. |
| Wi-Fi | Working | BCM4358 over PCIe; association, reconnect and wireless SSH tested. |
| Bluetooth | Working with limits | Firmware initialization, hci0 and scanning tested; pairing/audio profiles not qualified. |
| Display scanout | Working with limits | Firmware-initialized framebuffer through simpledrm; native panel lifecycle is not implemented. |
| GPU acceleration | Working with known faults | Panfrost rendering improves Plasma; intermittent scheduler timeouts remain. |
| Touchscreen and on-screen keyboard | Working | Physical touch/drag and keyboard input confirmed with Plasma userspace. |
| Home, Power, Volume, Back and Recents | Working with mapping caveats | Physical events confirmed; latest Back/wake/menu adjustments require further UI feedback. |
| Capacitive key backlight | Implemented, partially verified | LED/regulator path exists; visual operation still needs explicit confirmation. |
| GUI Wi-Fi/Bluetooth controls | Working in configured userspace | NetworkManager, BlueZ, D-Bus and policy configuration required. |
| Normal reboot and reboot to TWRP | Working | Userspace-controlled clean restart paths tested. |
| Physical power-off | Not hardware-qualified | Syscon driver registered in SYSTEM2; actual power cut not tested. |
| Screen blanking | Partial | Black framebuffer/DPMS path works; panel power and refresh remain active. |
| Suspend and GPU runtime power management | Not implemented | No deep-idle battery-life claim. |
| Speaker, microphone and audio routing | Not validated | No functional audio claim. |
| Cellular modem, calls and mobile data | Not implemented/validated | WLAN root complex does not initialize the modem controller. |
| Cameras, fingerprint, NFC and other sensors | Not validated | No support claim from this bring-up. |
