#!/usr/bin/env bash
# Installs the AirPods GNOME tray app. Run from inside a clone of this repo:
#
#   git clone https://github.com/TT-Hipster1941/airpods-gnome-tray.git
#   cd airpods-gnome-tray
#   ./install.sh
#
# This script installs the tray icon itself. It also needs a librepods
# daemon build that exposes $XDG_STATE_HOME/librepods/status.json and a
# `status` verb -- upstream librepods and the AUR packages built from it do
# not have these, so the daemon has to come from a fork that does. See the
# README for where that daemon comes from and how to build it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Installing runtime dependencies (pacman, needs sudo)"
sudo pacman -S --needed --noconfirm \
  gtk3 python-gobject libayatana-appindicator \
  gnome-shell-extension-appindicator

if ! command -v librepods-ctl >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/librepods-ctl" ]; then
    echo
    echo "!! librepods-ctl was not found on PATH or in ~/.local/bin."
    echo "   This tray app is only a front end -- it needs the daemon built"
    echo "   and running first. See README.md for where to get it and how"
    echo "   to build it, then re-run this script."
    echo
fi

echo "==> Installing the tray app"
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/airpods-panel-icons" \
         "$HOME/.local/share/applications" "$HOME/.config/autostart"

install -m755 "$SCRIPT_DIR/airpods-panel.py" "$HOME/.local/bin/airpods-panel.py"
install -m755 "$SCRIPT_DIR/airpods-panel-launch.sh" "$HOME/.local/bin/airpods-panel-launch.sh"
install -m644 "$SCRIPT_DIR/icons/apple-logo-symbolic.svg" \
  "$HOME/.local/share/airpods-panel-icons/apple-logo-symbolic.svg"

DESKTOP_ENTRY='[Desktop Entry]
Type=Application
Name=AirPods
Comment=AirPods battery and controls
Exec=/usr/bin/python3 '"$HOME"'/.local/bin/airpods-panel.py
Icon=audio-headphones-symbolic
Terminal=false
Categories=Utility;'

echo "$DESKTOP_ENTRY" > "$HOME/.local/share/applications/airpods-panel.desktop"
echo "$DESKTOP_ENTRY
X-GNOME-Autostart-enabled=true" > "$HOME/.config/autostart/airpods-panel.desktop"

echo "==> GNOME tray icon support"
# Without both of these, the icon either never shows, or GNOME reports the
# extension as enabled without ever actually activating it -- see the
# README's Troubleshooting section before assuming a relogin will fix it.
gsettings set org.gnome.shell disable-user-extensions false
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com || true

echo "==> Keyboard shortcut (Ctrl+Shift+Alt+P) to (re)launch the panel"
EXISTING=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
KEY_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/airpods0/"
if [[ "$EXISTING" != *"$KEY_PATH"* ]]; then
    if [ "$EXISTING" = "@as []" ]; then
        NEW="['$KEY_PATH']"
    else
        NEW="${EXISTING%]}, '$KEY_PATH']"
    fi
    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW"
fi
gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH" name "AirPods Panel"
gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH" command "$HOME/.local/bin/airpods-panel-launch.sh"
gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH" binding "<Control><Shift><Alt>p"

echo
echo "==> Done."
echo "    Pair your AirPods through GNOME's Bluetooth settings if you haven't,"
echo "    log out and back in once so the AppIndicator extension activates,"
echo "    then launch: ~/.local/bin/airpods-panel-launch.sh (or Ctrl+Shift+Alt+P)."
