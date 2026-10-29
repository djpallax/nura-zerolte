#!/rescue/bin/busybox sh
# Runs once during initial boot. No UDC disconnect, soft_connect or driver reset.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
/rescue/bin/busybox mount -t configfs configfs /sys/kernel/config
G=/sys/kernel/config/usb_gadget/net1
/rescue/bin/busybox mkdir "$G"
echo 0x0525 >"$G/idVendor"
echo 0xa4a7 >"$G/idProduct"
echo 0x0200 >"$G/bcdUSB"
echo 0x0100 >"$G/bcdDevice"
echo 0xef >"$G/bDeviceClass"
echo 2 >"$G/bDeviceSubClass"
echo 1 >"$G/bDeviceProtocol"
/rescue/bin/busybox mkdir "$G/strings/0x409"
echo NET1-SM-G925I >"$G/strings/0x409/serialnumber"
echo Samsung >"$G/strings/0x409/manufacturer"
echo 'Galaxy S6 Edge NET1 ACM ECM' >"$G/strings/0x409/product"
/rescue/bin/busybox mkdir "$G/configs/c.1"
/rescue/bin/busybox mkdir "$G/configs/c.1/strings/0x409"
echo 'ACM console + ECM network' >"$G/configs/c.1/strings/0x409/configuration"
echo 2 >"$G/configs/c.1/MaxPower"
/rescue/bin/busybox mkdir "$G/functions/acm.usb0"
/rescue/bin/busybox mkdir "$G/functions/ecm.usb0"
echo 02:74:20:00:00:01 >"$G/functions/ecm.usb0/host_addr"
echo 02:74:20:00:00:02 >"$G/functions/ecm.usb0/dev_addr"
/rescue/bin/busybox ln -s "$G/functions/acm.usb0" "$G/configs/c.1/acm.usb0"
/rescue/bin/busybox ln -s "$G/functions/ecm.usb0" "$G/configs/c.1/ecm.usb0"
# The sole UDC assignment registers the complete gadget at boot.
[ -d /sys/class/udc/15400000.usb ]
echo 15400000.usb >"$G/UDC"
/rescue/bin/busybox ifconfig usb0 192.168.77.2 netmask 255.255.255.252 up
echo NET1_GADGET_READY
