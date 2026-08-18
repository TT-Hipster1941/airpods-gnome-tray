# AirPods GNOME Tray

A GTK `AppIndicator` tray icon showing AirPods battery levels and controls
(noise mode, adaptive noise level, Conversation Awareness, One-Bud ANC, ear
detection) on GNOME/Wayland.

This is a front end only. It reads
`$XDG_STATE_HOME/librepods/status.json` on a timer and sends commands through
`librepods-ctl` — it never talks to Bluetooth itself, and does nothing if the
daemon isn't running.

## Requirements

- A `librepods` daemon build that writes `status.json` and understands the
  `status`, `ca:`, `onebud:`, `ear:` and `adaptive:N` verbs on top of the
  usual noise-mode ones. Upstream
  [kavishdevar/librepods](https://github.com/kavishdevar/librepods) and the
  AUR packages built from it do **not** have these — the daemon this app was
  built against is the fork in
  [thisisgm/omarchy-pods](https://github.com/thisisgm/omarchy-pods)
  (`daemon/`, GPL-3.0). Build it from there:

  ```bash
  git clone https://github.com/thisisgm/omarchy-pods.git
  cd omarchy-pods/daemon
  cmake -B build -G Ninja && cmake --build build
  cmake --install build --prefix ~/.local
  systemctl --user enable --now librepods.service
  ```

- AirPods paired to the machine through the usual GNOME Bluetooth flow —
  pairing keys are per-machine and can't be copied between computers.

## Install

```bash
git clone https://github.com/TT-Hipster1941/airpods-gnome-tray.git
cd airpods-gnome-tray
./install.sh
```

`install.sh` installs the GTK/AppIndicator runtime dependencies, the tray
script, a `.desktop` entry (with autostart), and binds `Ctrl+Shift+Alt+P` to
relaunch the panel if it's not already running. It does not build the daemon —
do that first, per Requirements above.

## Troubleshooting

**Tray icon never shows up, even after installing.** GNOME only draws
`AppIndicator`/`StatusNotifierItem` icons with the
`appindicatorsupport@rgcjonas.gmail.com` extension enabled, and only picks up
a newly-enabled extension on Wayland after a full logout/login — restarting
the app itself is not enough.

**Icon still missing after logging out and back in.** Check
`gsettings get org.gnome.shell disable-user-extensions` before anything else.
When that key is `true`, GNOME lets `gnome-extensions enable` run without
error and even reports the extension as present, while never actually
activating it — this looks exactly like a stuck extension that a relogin
should have fixed, but isn't one. `install.sh` sets it to `false` already;
this is only worth checking if something else on the machine has flipped it
back.

**Menu opens but shows only "Quit."** The menu is exported over the DBusMenu
protocol, which GNOME Shell reconstructs itself rather than showing a real
GTK popup, and DBusMenu only understands plain `Gtk.MenuItem` (label set via
the constructor), `Gtk.CheckMenuItem`, `Gtk.RadioMenuItem`,
`Gtk.SeparatorMenuItem` and submenus. A custom widget added to a menu item
with `.add()` — a `Gtk.Box`, a `Gtk.Scale`, a `Gtk.ComboBoxText` — is silently
dropped rather than shown. `airpods-panel.py` only uses the supported types
for this reason; if you're modifying it, keep it that way.

## Limitations

AppIndicator tray icons have no way to be told to pop their menu open from
the outside, so the keyboard shortcut only makes sure the tray process is
running — you still click the icon to see the menu.

## Uninstall

```bash
pkill -f airpods-panel.py || true
rm -f ~/.local/bin/airpods-panel.py ~/.local/bin/airpods-panel-launch.sh \
      ~/.local/share/applications/airpods-panel.desktop \
      ~/.config/autostart/airpods-panel.desktop
rm -rf ~/.local/share/airpods-panel-icons
```

This doesn't touch the daemon; see the daemon repo for removing that
separately.

## Licence

MIT, see [LICENSE](LICENSE). This is a separate program from the daemon it
talks to over a state file and a command line — it doesn't bundle or link
against the daemon's GPL-3.0 code.
