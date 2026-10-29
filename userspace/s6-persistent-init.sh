#!/rescue/bin/busybox sh
# Alpine root lives directly in initramfs RAM. No disk discovery or mounting.
export PATH=/bin:/sbin:/usr/bin:/usr/sbin HOME=/root TERM=linux
BB=/rescue/bin/busybox
$BB mkdir -p /dev /proc /sys /run /tmp /dev/pts /root/.ssh
[ -c /dev/tty0 ] || $BB mount -t devtmpfs devtmpfs /dev
[ -r /proc/self/stat ] || $BB mount -t proc proc /proc
[ -d /sys/class ] || $BB mount -t sysfs sysfs /sys
$BB mount -t tmpfs -o size=16m,mode=755 tmpfs /run
$BB mount -t tmpfs -o size=64m,mode=1777 tmpfs /tmp
$BB mkdir -p /dev/pts /run/openrc
$BB mount -t devpts -o mode=620,ptmxmode=666 devpts /dev/pts
$BB chmod 700 /root /root/.ssh
$BB hostname s6-nura
$BB date -u -s "@$(cat /etc/s6-build-epoch)" >/dev/null 2>&1 || :
[ ! -c /dev/console ] || exec </dev/console >/dev/console 2>&1
echo 'ROOTFS1: Nura v26.06 on USERDATA, static USB rescue console retained'
# Same CONSOLEFIX1 supervision independently of OpenRC/SSH.
(
  $BB sleep 2
  while :; do
    if [ -c /dev/ttyGS0 ]; then
      echo 'CF1: opening ttyGS0 (persistent-root rescue)' >>/run/consolefix1-serial.log
      $BB sh -i </dev/ttyGS0 >/dev/ttyGS0 2>&1
    fi
    $BB sleep 2
  done
) </dev/null >/dev/null 2>&1 &
$BB timeout 25 /sbin/ramroot1-usb-setup >/run/ramroot1-usb.log 2>&1 || echo RAMROOT1_USB_SETUP_FAILED
$BB ifconfig lo 127.0.0.1 up
# Bound writable RAM filesystems; limits reserve no physical memory up front.
echo ROOTFS1_NURA_INIT_REACHED >/dev/kmsg
if [ -c /dev/tty0 ]; then
  printf '\033[0m\033[2J\033[H' >/dev/tty0
  echo 'GALAXY S6 EDGE - NURA ROOTFS1' >/dev/tty0
  echo 'ACM rescue shell + ECM/SSH. Persistent root on USERDATA.' >/dev/tty0
fi
exec /sbin/init
