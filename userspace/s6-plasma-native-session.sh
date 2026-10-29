#!/bin/sh
# Hardware EGL/GBM on SimpleDRM + Panfrost. Direct single-seat pilot.
set -eu
cd "$HOME"
umask 077
unset DISPLAY XAUTHORITY WAYLAND_DISPLAY LIBGL_ALWAYS_SOFTWARE QT_QUICK_BACKEND QSG_RENDER_LOOP LP_NUM_THREADS
export SHELL=/bin/sh
export XDG_RUNTIME_DIR=/run/s6-native/runtime XDG_CACHE_HOME=/run/s6-native/cache
export XDG_CONFIG_DIRS="$HOME/.config/plasma-mobile:/etc/xdg" XDG_MENU_PREFIX=plasma-
export XDG_CURRENT_DESKTOP=KDE XDG_SESSION_DESKTOP=KDE XDG_SESSION_TYPE=wayland
export KDE_FULL_SESSION=true KDE_SESSION_VERSION=6 PLASMA_PLATFORM=phone:handset
export KWIN_IM_SHOW_ALWAYS=1 KWIN_COMPOSE=O2ES
export KWIN_DRM_DEVICES=/dev/dri/card0
export QSG_RHI_BACKEND=opengl
# Keep Qt scenegraph diagnostics opt-in; avoid verbose logs in normal use.
export QT_ENABLE_HIGHDPI_SCALING=1 QT_AUTO_SCREEN_SCALE_FACTOR=0
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
export MESA_SHADER_CACHE_MAX_SIZE=32M
export HISTFILE=/run/s6-native/ash_history
exec dbus-run-session -- env LD_PRELOAD=/usr/local/lib/s6-kwin-drm-nonblock.so kwin_wayland --drm --xwayland --socket wayland-s6-native \
 --no-lockscreen --inputmethod /usr/bin/plasma-keyboard \
 --exit-with-session /usr/local/bin/s6-plasma-native-shell
