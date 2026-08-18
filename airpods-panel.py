#!/usr/bin/env python3
# Copyright (C) 2026 TT-Hipster1941
# Licensed under the GNU GPL v3 or later. See LICENSE.
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import Gtk, AyatanaAppIndicator3, GLib

import json
import os
import subprocess

STATUS_PATH = os.path.join(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
    "librepods", "status.json",
)
CTL_PATH = os.path.expanduser("~/.local/bin/librepods-ctl")

NOISE_MODES = [("Off", "noise:off"), ("ANC", "noise:anc"),
               ("Transparency", "noise:transparency"), ("Adaptive", "noise:adaptive")]
ADAPTIVE_LEVELS = [25, 50, 75, 100]
EAR_MODES = [("Pause when one is out", "ear:one"),
             ("Pause when both are out", "ear:both"),
             ("Never pause", "ear:off")]


def send(verb):
    try:
        subprocess.Popen([CTL_PATH, verb],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def read_status():
    try:
        with open(STATUS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def battery_label(pod):
    if not pod.get("available"):
        return "--"
    level = pod.get("level", 0)
    charging = " (charging)" if pod.get("charging") else ""
    return f"{level}%{charging}"


def static_item(label=""):
    item = Gtk.MenuItem(label=label)
    item.set_sensitive(False)
    return item


class AirPodsIndicator:
    def __init__(self):
        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "airpods-panel",
            "apple-logo-symbolic",
            AyatanaAppIndicator3.IndicatorCategory.HARDWARE,
        )
        self.indicator.set_icon_theme_path(
            os.path.expanduser("~/.local/share/airpods-panel-icons"))
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)
        self._shape = None
        self._w = {}
        self._updating = False
        GLib.timeout_add_seconds(2, self._refresh)
        self._refresh()

    # -- structural helpers (only called when the menu's shape changes) --

    def _set_menu_items(self, items):
        for child in self.menu.get_children():
            self.menu.remove(child)
        for item in items:
            self.menu.append(item)
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda *_: Gtk.main_quit())
        self.menu.append(quit_item)
        self.menu.show_all()

    def _build_radio_group(self, labels, on_select):
        items = []
        group = None
        for idx, text in enumerate(labels):
            item = Gtk.RadioMenuItem.new_with_label_from_widget(group, text)
            group = item
            item.connect("toggled", self._make_radio_handler(idx, on_select))
            items.append(item)
        return items

    def _make_radio_handler(self, idx, on_select):
        def handler(widget):
            if self._updating or not widget.get_active():
                return
            on_select(idx)
        return handler

    def _set_active_radio(self, items, index):
        self._updating = True
        for i, item in enumerate(items):
            item.set_active(i == index)
        self._updating = False

    def _set_active_check(self, item, active):
        if item.get_active() == active:
            return
        self._updating = True
        item.set_active(active)
        self._updating = False

    def _build_static_shape(self, text):
        item = static_item(text)
        self._w = {"message": item}
        self._set_menu_items([item])

    def _build_connected_shape(self, is_pro, adaptive_shown):
        w = {}
        items = []

        w["title"] = static_item()
        items.append(w["title"])
        items.append(Gtk.SeparatorMenuItem())

        for key in ("left", "right", "case"):
            w[f"batt_{key}"] = static_item()
            items.append(w[f"batt_{key}"])
        items.append(Gtk.SeparatorMenuItem())

        w["noise_radios"] = self._build_radio_group(
            [m[0] for m in NOISE_MODES], lambda i: send(NOISE_MODES[i][1]))
        noise_submenu = Gtk.Menu()
        for item in w["noise_radios"]:
            noise_submenu.append(item)
        noise_submenu.show_all()
        noise_root = Gtk.MenuItem(label="Noise Control")
        noise_root.set_submenu(noise_submenu)
        items.append(noise_root)

        if adaptive_shown:
            w["adaptive_radios"] = self._build_radio_group(
                [f"{v}%" for v in ADAPTIVE_LEVELS],
                lambda i: send(f"adaptive:{ADAPTIVE_LEVELS[i]}"))
            level_submenu = Gtk.Menu()
            for item in w["adaptive_radios"]:
                level_submenu.append(item)
            level_submenu.show_all()
            level_root = Gtk.MenuItem(label="Adaptive Level")
            level_root.set_submenu(level_submenu)
            items.append(level_root)

        if is_pro:
            w["ca"] = Gtk.CheckMenuItem(label="Conversation Awareness")
            w["ca"].connect("toggled", lambda widget: (
                None if self._updating else send("ca:on" if widget.get_active() else "ca:off")))
            items.append(w["ca"])

            w["onebud"] = Gtk.CheckMenuItem(label="One-Bud ANC")
            w["onebud"].connect("toggled", lambda widget: (
                None if self._updating else send("onebud:on" if widget.get_active() else "onebud:off")))
            items.append(w["onebud"])

        items.append(Gtk.SeparatorMenuItem())

        w["ear_radios"] = self._build_radio_group(
            [m[0] for m in EAR_MODES], lambda i: send(EAR_MODES[i][1]))
        ear_submenu = Gtk.Menu()
        for item in w["ear_radios"]:
            ear_submenu.append(item)
        ear_submenu.show_all()
        ear_root = Gtk.MenuItem(label="Ear Detection")
        ear_root.set_submenu(ear_submenu)
        items.append(ear_root)

        self._w = w
        self._set_menu_items(items)

    # -- value-only refresh (no structural change, no visible glitch) --

    def _update_connected_values(self, status, noise_mode):
        w = self._w
        name = status.get("device_name") or "AirPods"
        w["title"].set_label(name)

        for key, caption in (("left", "Left"), ("right", "Right"), ("case", "Case")):
            pod = status.get(key, {})
            w[f"batt_{key}"].set_label(f"{caption}: {battery_label(pod)}")

        self._set_active_radio(w["noise_radios"], noise_mode)

        if "adaptive_radios" in w:
            level = status.get("adaptive_noise_level", 50)
            closest = min(range(len(ADAPTIVE_LEVELS)),
                          key=lambda i: abs(ADAPTIVE_LEVELS[i] - level))
            self._set_active_radio(w["adaptive_radios"], closest)

        if "ca" in w:
            self._set_active_check(w["ca"], bool(status.get("conversational_awareness")))
        if "onebud" in w:
            self._set_active_check(w["onebud"], bool(status.get("one_bud_anc_mode")))

        behavior = status.get("ear_detection_behavior", 0)
        self._set_active_radio(w["ear_radios"], behavior)

    def _refresh(self):
        status = read_status()

        if status is None:
            if self._shape != "none":
                self._build_static_shape("librepods is not running")
                self._shape = "none"
            return True

        if not status.get("connected", False):
            if self._shape != "disconnected":
                self._build_static_shape("Not connected")
                self._shape = "disconnected"
            return True

        noise_mode = status.get("noise_mode", -1)
        is_pro = bool(status.get("is_pro_series"))
        adaptive_shown = noise_mode == 3
        shape = ("connected", is_pro, adaptive_shown)

        if shape != self._shape:
            self._build_connected_shape(is_pro, adaptive_shown)
            self._shape = shape

        self._update_connected_values(status, noise_mode)
        return True


if __name__ == "__main__":
    AirPodsIndicator()
    Gtk.main()
