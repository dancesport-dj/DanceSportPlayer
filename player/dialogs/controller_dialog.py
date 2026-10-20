"""🎛 The hardware controller's window: which device, which profile, and what
each knob or button does — learned by pressing it.

Every change applies at once and is saved; there is nothing to confirm.
While a row is learning, the controller's readings go to this window instead
of the desk, so the press that teaches a button does not also fire it.
"""
from pathlib import Path

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                               QMenu, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from planner.playing import controller as pctl
from planner import i18n
from planner.config import APP_DIR
from player.window.main_controller import controller_devices

_COL_ACTION, _COL_CONTROL, _COL_LEARN, _COL_CLEAR = range(4)


def action_label(action: str) -> str:
    """An action as the window lists it, in the app's language."""
    if action.startswith("pad:"):
        return i18n.t("🎛  Cartwall pad %d") % int(action[4:])
    return i18n.t(dict(pctl.ACTIONS)[action])


def profile_dir() -> Path:
    """Where profiles are offered to load from and save to by default."""
    path = Path(APP_DIR) / "controllers"
    path.mkdir(parents=True, exist_ok=True)
    return path


class ControllerDialog(QDialog):
    """Non-modal; the main window keeps one and shows it again."""

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self._host = host
        self._learning = None
        self._moved = {}     # action → the action Learn gave its control to
        self._swept = set()  # the CCs seen between 0 and 127: knobs, faders
        self.setWindowTitle("🎛  Controller")
        self.setMinimumSize(560, 620)
        lyt = QVBoxLayout(self)

        info = QLabel(
            "Play, skip, fade, set the volume and fire cartwall pads from a USB "
            "MIDI controller (e.g. Korg nanoKONTROL2) or a HID one (e.g. a "
            "Traktor controller in its native mode). Pick the device, load a "
            "profile or click Learn and press the button that should do it.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#666; font-size:11px;")
        lyt.addWidget(info)

        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("Device:"))
        self._device = QComboBox()
        self._device.activated.connect(self._on_device_chosen)
        dev_row.addWidget(self._device, stretch=1)
        refresh = QPushButton("↻")
        refresh.setToolTip("Look for devices again")
        refresh.clicked.connect(self._fill_devices)
        dev_row.addWidget(refresh)
        lyt.addLayout(dev_row)
        self._all_hid = QCheckBox("Show all HID devices, not only DJ controllers")
        self._all_hid.toggled.connect(self._fill_devices)
        lyt.addWidget(self._all_hid)
        self._status = QLabel()
        self._status.setWordWrap(True)
        lyt.addWidget(self._status)

        prof_row = QHBoxLayout()
        self._profile = QLabel()
        prof_row.addWidget(self._profile, stretch=1)
        presets_btn = QPushButton("Presets ▾")
        menu = QMenu(presets_btn)
        for name in pctl.PRESETS:
            menu.addAction(name, lambda n=name: self._apply_preset(n))
        presets_btn.setMenu(menu)
        # The caption's ▾ is the arrow; Qt's own indicator would be a second.
        presets_btn.setStyleSheet("QPushButton::menu-indicator { image: none; width: 0; }")
        prof_row.addWidget(presets_btn)
        load_btn = QPushButton("📂  Load profile…")
        load_btn.clicked.connect(self._load_profile)
        prof_row.addWidget(load_btn)
        save_btn = QPushButton("💾  Save profile…")
        save_btn.clicked.connect(self._save_profile)
        prof_row.addWidget(save_btn)
        lyt.addLayout(prof_row)

        self._table = QTableWidget(len(pctl.ACTIONS), 4)
        self._table.setHorizontalHeaderLabels(["Action", "Control", "", ""])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        head = self._table.horizontalHeader()
        head.setSectionResizeMode(_COL_ACTION, QHeaderView.ResizeMode.Stretch)
        head.setSectionResizeMode(_COL_CONTROL, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(_COL_LEARN, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(_COL_CLEAR, QHeaderView.ResizeMode.ResizeToContents)
        self._learn_btns = {}
        self._clear_btns = {}
        for row, action in enumerate(pctl.ACTION_IDS):
            self._table.setItem(row, _COL_ACTION, QTableWidgetItem(action_label(action)))
            self._table.setItem(row, _COL_CONTROL, QTableWidgetItem(""))
            learn = QPushButton("Learn")
            learn.setCheckable(True)
            learn.clicked.connect(lambda _c=False, a=action: self._toggle_learn(a))
            self._table.setCellWidget(row, _COL_LEARN, learn)
            self._learn_btns[action] = learn
            clear = QPushButton("✕")
            clear.setToolTip("Unbind this action")
            clear.clicked.connect(lambda _c=False, a=action: self._clear(a))
            self._table.setCellWidget(row, _COL_CLEAR, clear)
            self._clear_btns[action] = clear
        lyt.addWidget(self._table, stretch=1)

        self._last = QLabel(" ")
        self._last.setStyleSheet("color:#666;")
        lyt.addWidget(self._last)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        lyt.addWidget(box)

        hub = host.controller_hub()
        hub.changed.connect(self._sync_status)
        hub.control.connect(self._on_reading)
        self._fill_devices()
        self._sync_table()

    # ── State ────────────────────────────────────────────────────────────────

    def _cfg(self) -> dict:
        return self._host.controller_config()

    def _store(self, **changes):
        cfg = self._cfg()
        cfg.update(changes)
        self._host.set_controller_config(cfg)
        self._sync_table()

    def _fill_devices(self):
        cfg = self._cfg()
        self._device.clear()
        self._device.addItem(i18n.t("— none —"), ("", ""))
        found = False
        for kind, ident, name in controller_devices(self._all_hid.isChecked()):
            self._device.addItem(name, (kind, ident))
            if (kind, ident) == (cfg["kind"], cfg["device"]):
                self._device.setCurrentIndex(self._device.count() - 1)
                found = True
        if cfg["device"] and not found:
            self._device.addItem(i18n.t("%s — not plugged in") % cfg["device"],
                                 (cfg["kind"], cfg["device"]))
            self._device.setCurrentIndex(self._device.count() - 1)
        self._sync_status()

    def _sync_status(self):
        connected, text = self._host.controller_status()
        if connected:
            self._status.setText(i18n.t("● Connected — %s") % text)
            self._status.setStyleSheet("color:#2e7d32; font-weight:bold;")
        elif self._cfg()["device"]:
            self._status.setText(i18n.t("○ Not connected — %s") % text)
            self._status.setStyleSheet("color:#c62828;")
        else:
            self._status.setText(i18n.t("No controller chosen."))
            self._status.setStyleSheet("color:#666;")

    def _sync_table(self):
        cfg = self._cfg()
        self._profile.setText(i18n.t("Profile: %s") % (cfg["profile"] or i18n.t("own")))
        faders = {"vol_up": "volume", "vol_down": "volume",
                  "cart_vol_up": "cart_volume", "cart_vol_down": "cart_volume"}
        # A row that has a control again needs no note on where its old one went.
        self._moved = {a: b for a, b in self._moved.items()
                       if not cfg["bindings"].get(a)}
        for row, (action, _label) in enumerate(pctl.ACTIONS):
            control = cfg["bindings"].get(action, "")
            text = pctl.control_label(control) if control else ""
            moved = not control and action in self._moved
            if moved:
                text = i18n.t("⚠ moved to %s") % action_label(self._moved[action])
            fader = cfg["bindings"].get(faders.get(action, ""), "")
            covered = not control and fader
            if covered:
                # 🔼/🔽 are the 🔊 fader's job already: an empty cell would
                # read as if nothing set the volume.
                text = i18n.t("on the fader — %s") % pctl.control_label(fader)
            learning = action == self._learning
            if learning:
                text = i18n.t("Press or move a control…")
            item = self._table.item(row, _COL_CONTROL)
            if item is not None:
                item.setText(text)
                item.setForeground(QBrush(QColor("#888")) if covered and not learning
                                   else QBrush(QColor("#b26a00")) if moved and not learning
                                   else QBrush())
            btn = self._learn_btns[action]
            btn.setChecked(learning)
            btn.setText(i18n.t("Cancel") if learning else i18n.t("Learn"))

    # ── Device and profile ───────────────────────────────────────────────────

    def _on_device_chosen(self, index: int):
        kind, ident = self._device.itemData(index) or ("", "")
        self._store(kind=kind, device=ident)

    def _pick_device_for(self, hint: str):
        """After a preset or a profile: its device, if it is plugged in and
        none is chosen yet."""
        if self._cfg()["device"] or not hint:
            return
        for kind, ident, name in controller_devices(self._all_hid.isChecked()):
            if hint.lower() in name.lower():
                self._store(kind=kind, device=ident)
                self._fill_devices()
                return

    def _apply_preset(self, name: str):
        self._moved = {}
        preset = pctl.PRESETS[name]
        self._store(profile=name, bindings=dict(preset["bindings"]))
        self._pick_device_for(preset["device"])

    def _load_profile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.t("Load controller profile"), str(profile_dir()),
            i18n.t("Controller profiles (*.json)"))
        if not path:
            return
        try:
            prof = pctl.load_profile(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, i18n.t("🎛  Controller"),
                                i18n.t("This file is not a controller profile:\n%s")
                                % exc)
            return
        self._moved = {}
        self._store(profile=prof["name"], bindings=prof["bindings"])
        self._pick_device_for(prof["device"])

    def _save_profile(self):
        cfg = self._cfg()
        name = cfg["profile"] or cfg["device"] or "controller"
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.t("Save controller profile"),
            str(profile_dir() / f"{name}.json"),
            i18n.t("Controller profiles (*.json)"))
        if not path:
            return
        try:
            pctl.save_profile(path, Path(path).stem, cfg["device"], cfg["bindings"])
        except OSError as exc:
            QMessageBox.warning(self, i18n.t("🎛  Controller"),
                                i18n.t("Could not save the profile:\n%s") % exc)
            return
        self._store(profile=Path(path).stem)

    # ── Learn ────────────────────────────────────────────────────────────────

    def _toggle_learn(self, action: str):
        self._learning = None if self._learning == action else action
        self._host.set_controller_listener(
            self._on_learn if self._learning else None)
        self._sync_table()

    def _on_learn(self, control: str, value: float):
        action = self._learning
        if action is None or not pctl.learn_takes(action, control, value,
                                                  self._swept):
            return
        self._learning = None
        self._host.set_controller_listener(None)
        bindings = self._cfg()["bindings"]
        # Learn moves a taken control rather than binding it twice — and says
        # so on the row that lost it, which would otherwise just go blank.
        for other, had in bindings.items():
            if had == control and other != action:
                self._moved[other] = action
        self._store(profile="", bindings=pctl.bind(bindings, action, control))

    def _clear(self, action: str):
        """✕ unbinds — but while a row is learning it stops that first, and
        on the learning row itself does nothing more."""
        learning = self._learning
        if learning is not None:
            self._toggle_learn(learning)
            if learning == action:
                return
        bindings = dict(self._cfg()["bindings"])
        if bindings.pop(action, None) is not None:
            self._store(profile="", bindings=bindings)

    def _on_reading(self, control: str, value: float):
        """The last control touched, and what it is bound to — so a button
        that does nothing shows why."""
        bound = {c: a for a, c in self._cfg()["bindings"].items()}.get(control)
        label = action_label(bound) if bound else i18n.t("not bound")
        self._last.setText(i18n.t("Last: %(control)s = %(value)d%% → %(action)s")
                           % {"control": pctl.control_label(control),
                              "value": round(value * 100), "action": label})

    def done(self, result):
        if self._learning is not None:
            self._learning = None
            self._host.set_controller_listener(None)
        hub = self._host.controller_hub()
        for signal, slot in ((hub.changed, self._sync_status),
                             (hub.control, self._on_reading)):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        super().done(result)
