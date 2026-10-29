#!/bin/sh
# Serialize callbacks and inspect current state, rather than replay stale events.
[ "$1" = wlan0 ] || exit 0
case "$2" in up|down|dhcp4-change) ;; *) exit 0;; esac
(
 n=0
 until mkdir /run/s6-nm-ssh.lock 2>/dev/null; do
  n=$((n+1)); [ "$n" -lt 20 ] || exit 1; sleep 1
 done
 trap 'rmdir /run/s6-nm-ssh.lock' EXIT
 sleep 1
 for attempt in 1 2 3; do
  address=$(ip -4 addr show dev wlan0 | awk '/inet / {split($2,a,"/");print a[1];exit}')
  previous=$(cat /run/s6-wlan-listen-address 2>/dev/null || true)
  pid=$(cat /run/s6-wlan-ssh.pid 2>/dev/null || true)
  if [ -n "$address" ] && [ "$address" = "$previous" ] && [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then exit 0;fi
  if [ -z "$address" ]; then
   timeout 10 /etc/init.d/s6-wlan-ssh stop || true
   exit 0
  fi
  if timeout 15 /etc/init.d/s6-wlan-ssh restart; then exit 0;fi
  sleep 2
 done
 exit 1
) </dev/null >>/run/s6-nm-ssh.log 2>&1 &
exit 0
