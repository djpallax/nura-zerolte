#!/bin/sh
set -eu
export QT_QPA_PLATFORM=wayland
exec swayidle -w timeout 120 '/usr/local/bin/s6-screen-state off' resume '/usr/local/bin/s6-screen-state on'
