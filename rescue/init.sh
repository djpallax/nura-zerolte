#!/rescue/bin/busybox sh
# RAM rescue by default; USERDATA handoff is an explicit build-time option.
export PATH=/bin:/sbin:/rescue/bin HOME=/root TERM=linux
BB=/rescue/bin/busybox
$BB mkdir -p /dev /proc /sys /run /tmp /bin /newroot
$BB mount -t devtmpfs devtmpfs /dev
$BB mount -t proc proc /proc
$BB mount -t sysfs sysfs /sys
$BB mount -t tmpfs -o size=16m,mode=755 tmpfs /run
$BB mount -t tmpfs -o size=32m,mode=1777 tmpfs /tmp
$BB --install -s /bin
[ ! -c /dev/console ] || exec </dev/console >/dev/console 2>&1
# Do not interpret another owner's filesystem as an installation of this port.
if [ "$(cat /etc/s6-root-mode)" = userdata ]; then
 i=0; target=
 while [ "$i" -lt 25 ]; do
  target=
  for u in /sys/class/block/sd*/uevent; do
   [ -r "$u" ] || continue
   if $BB grep -q '^PARTNAME=USERDATA$' "$u"; then
    [ -z "$target" ] || { target=ambiguous; break; }
    name=${u%/uevent}; target=/dev/${name##*/}
   fi
  done
  [ -z "$target" ] || break
  $BB sleep 1; i=$((i+1))
 done
 if [ -b "$target" ] && $BB timeout 15 $BB mount -t ext4 -o ro,noload "$target" /newroot; then
  if $BB grep -q '^S6-NURA-' /newroot/etc/s6-install-id 2>/dev/null &&
     $BB grep -Eq '^ID="?(nura|postmarketos)"?$' /newroot/etc/os-release &&
     [ -x /newroot/sbin/s6-persistent-init ] &&
     [ -x /newroot/rescue/bin/busybox ]; then
   # Reopen normally so ext4 loads/replays its journal only after validation.
   $BB umount /newroot
   if $BB timeout 15 $BB mount -t ext4 -o rw,noatime "$target" /newroot; then
    $BB mkdir -p /newroot/dev /newroot/proc /newroot/sys
    # No background processes/gadget have been started before switching roots.
    $BB mount --move /dev /newroot/dev &&
    $BB mount --move /proc /newroot/proc &&
    $BB mount --move /sys /newroot/sys &&
    exec $BB switch_root /newroot /sbin/s6-persistent-init
   fi
  fi
  $BB umount /newroot
 fi
 echo 'No compatible persistent root; using RAM rescue.' >/dev/kmsg
fi
# Rescue never mounts persistent partitions; make discovered block devices RO.
(
 while :; do
  for p in /dev/sd*; do [ ! -b "$p" ] || $BB blockdev --setro "$p"; done
  $BB sleep 3
 done
) </dev/null >/dev/null 2>&1 &
# CONSOLEFIX1 pattern: respawn the USB shell without any controller rebind.
(
 $BB sleep 2
 while :; do
  [ ! -c /dev/ttyGS0 ] || $BB sh -i </dev/ttyGS0 >/dev/ttyGS0 2>&1
  $BB sleep 2
 done
) </dev/null >/dev/null 2>&1 &
$BB timeout 25 $BB sh /sbin/s6-usb-setup >/run/usb.log 2>&1 || echo 'USB setup failed; see /run/usb.log.'
echo 'Zerolte RAM rescue. USB serial shell; /sbin/reboot-recovery returns to TWRP.'
while :; do $BB sleep 3600; done
