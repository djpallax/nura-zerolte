#!/bin/sh
set -eu
export QT_QPA_PLATFORM=wayland
export QT_QPA_PLATFORMTHEME=KDE QT_QUICK_CONTROLS_STYLE=org.kde.breeze
export QT_QUICK_CONTROLS_MOBILE=true PLASMA_PLATFORM=phone:handset
dbus-update-activation-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR XDG_CURRENT_DESKTOP XDG_SESSION_TYPE QT_QPA_PLATFORM
QT_QPA_PLATFORM=offscreen plasma-mobile-envmanager --apply-settings
timeout 8 kscreen-doctor -o > /run/s6-native/outputs-before.log 2>&1 || true
timeout 8 kscreen-doctor output.1.scale.3 > /run/s6-native/scale.log 2>&1 || true
# Screen idle is optional so a missing helper never prevents the desktop.
if command -v swayidle >/dev/null && [ -x /usr/local/bin/s6-power1-idle ]; then
 /usr/local/bin/s6-power1-idle > /run/s6-native/idle.log 2>&1 &
fi
if [ -x /usr/local/bin/s6-system1-buttons ]; then
 /usr/local/bin/s6-system1-buttons > /run/s6-native/buttons.log 2>&1 &
fi
exec /usr/bin/plasmashell -p org.kde.plasma.mobileshell
