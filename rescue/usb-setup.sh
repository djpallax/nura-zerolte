#!/rescue/bin/busybox sh
# One initial gadget bind. Never reset, disconnect or unbind DWC3.
set -eu
BB=/rescue/bin/busybox
$BB mkdir -p /sys/kernel/config
$BB mount -t configfs configfs /sys/kernel/config
G=/sys/kernel/config/usb_gadget/net1
$BB mkdir "$G"
echo 0x0525 >"$G/idVendor"
echo 0xa4a7 >"$G/idProduct"
echo 0x0200 >"$G/bcdUSB"
echo 0x0100 >"$G/bcdDevice"
echo 0xef >"$G/bDeviceClass"
echo 2 >"$G/bDeviceSubClass"
echo 1 >"$G/bDeviceProtocol"
$BB mkdir -p "$G/strings/0x409" "$G/configs/c.1/strings/0x409"
echo zerolte-rescue >"$G/strings/0x409/serialnumber"
echo Samsung >"$G/strings/0x409/manufacturer"
echo 'Zerolte rescue ACM ECM' >"$G/strings/0x409/product"
echo 'ACM console and ECM network' >"$G/configs/c.1/strings/0x409/configuration"
echo 2 >"$G/configs/c.1/MaxPower"
$BB mkdir "$G/functions/acm.usb0" "$G/functions/ecm.usb0"
# Locally administered temporary addresses, not a copied device identity.
seed=$($BB od -An -N4 -tx1 /dev/urandom | $BB tr -d ' \n')
a=$($BB echo "$seed" | $BB cut -c1-2); b=$($BB echo "$seed" | $BB cut -c3-4)
c=$($BB echo "$seed" | $BB cut -c5-6); d=$($BB echo "$seed" | $BB cut -c7-8)
echo "02:$a:$b:$c:$d:01" >"$G/functions/ecm.usb0/host_addr"
echo "02:$a:$b:$c:$d:02" >"$G/functions/ecm.usb0/dev_addr"
$BB ln -s "$G/functions/acm.usb0" "$G/configs/c.1/acm.usb0"
$BB ln -s "$G/functions/ecm.usb0" "$G/configs/c.1/ecm.usb0"
i=0
while [ ! -d /sys/class/udc/15400000.usb ] && [ "$i" -lt 10 ]; do
 $BB sleep 1; i=$((i+1))
done
[ -d /sys/class/udc/15400000.usb ]
echo 15400000.usb >"$G/UDC"
$BB ifconfig usb0 192.168.77.2 netmask 255.255.255.252 up
