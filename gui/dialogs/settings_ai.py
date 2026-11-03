"""🤖 The Settings dialog's AI tab: the OpenRouter key and which of the host's
models to use, and whether that model answers before the claude CLI does.

None of it is a setting like the others. It lives in openrouter_config.json, so
the key stays out of settings.json and out of every venue pack: the dialog's OK
calls save_ai_config(), and values() never holds it.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.settings_look import _DialogHost
from gui.workers import OpenRouterModelsWorker
from planner import i18n
from planner.generate import ai

_MAMMOUTH = "https://api.mammouth.ai/v1"


class AiTabMixin(_DialogHost):
    """The 🤖 AI tab of SettingsDialog."""

    def _setup_ai_tab(self, tabs):
        cfg = ai.load_openrouter_config()
        ai_tab = QWidget()
        alyt = QVBoxLayout(ai_tab)
        alyt.setSpacing(10)
        intro = QLabel(
            "The 🤖 AI Playlist runs on the claude CLI. OpenRouter is the second "
            "way to reach a model: any model in its list, on your own key.")
        intro.setWordWrap(True)
        alyt.addWidget(intro)

        box = QGroupBox("🤖  OpenRouter connection")
        blyt = QVBoxLayout(box)

        brow = QHBoxLayout()
        brow.addWidget(QLabel("API base URL:"))
        self._ai_base = QComboBox()
        self._ai_base.setEditable(True)
        self._ai_base.addItems([ai.DEFAULT_API_BASE, _MAMMOUTH])
        self._ai_base.setCurrentText(cfg.get("base_url") or ai.DEFAULT_API_BASE)
        self._ai_base.setToolTip("Any OpenAI-compatible /chat/completions host.")
        brow.addWidget(self._ai_base, stretch=1)
        blyt.addLayout(brow)

        krow = QHBoxLayout()
        krow.addWidget(QLabel("API key:"))
        self._ai_key = QLineEdit(cfg.get("api_key", ""))
        self._ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._ai_key.setPlaceholderText("sk-or-…")
        self._ai_key.setToolTip(
            "From openrouter.ai/keys. Kept on this PC only, never in a venue pack.")
        krow.addWidget(self._ai_key, stretch=1)
        blyt.addLayout(krow)

        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Model:"))
        self._ai_model = QComboBox()
        self._ai_model.setEditable(True)
        self._ai_model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._ai_model.addItem(cfg.get("model", ""))
        # Hundreds of ids: typing any part of one finds it.
        completer = self._ai_model.completer()
        if completer is not None:
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._ai_model.setToolTip(
            "The exact model ID. Load models fills this list from the host;\n"
            "type any part of a name to find it.")
        mrow.addWidget(self._ai_model, stretch=1)
        self._ai_load = QPushButton("Load models")
        self._ai_load.clicked.connect(self._load_ai_models)
        mrow.addWidget(self._ai_load)
        blyt.addLayout(mrow)

        self._ai_status = QLabel("")
        self._ai_status.setWordWrap(True)
        self._ai_status.setStyleSheet("color:#666; font-size:11px;")
        blyt.addWidget(self._ai_status)

        self._ai_first = QCheckBox(
            "Ask this model first — the claude CLI becomes the fallback")
        self._ai_first.setChecked(bool(cfg.get("ask_first")))
        self._ai_first.setToolTip(
            "Off: the claude CLI answers, this model steps in when that fails.\n"
            "On: this model answers, the CLI steps in when it fails.")
        blyt.addWidget(self._ai_first)
        alyt.addWidget(box)
        alyt.addStretch()

        self._ai_given = self.ai_values()
        return tabs.addTab(ai_tab, "🤖 AI")

    def _load_ai_models(self):
        self._ai_load.setEnabled(False)
        self._ai_status.setText("Fetching the model list…")
        # On the window: Settings can close while the host thinks, and a QThread
        # must outlive it. The window waits for its threads at quit.
        worker = OpenRouterModelsWorker(
            self._ai_key.text().strip(), self.parent() or self,
            base_url=self._ai_base.currentText().strip(), free_only=False)
        worker.done.connect(self._on_ai_models)
        worker.error.connect(self._on_ai_models_error)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_ai_models(self, models):
        current = self._ai_model.currentText()
        self._ai_model.clear()
        self._ai_model.addItems(models)
        self._ai_model.setCurrentText(current)
        self._ai_status.setText(i18n.t("%d models loaded.") % len(models))
        self._ai_load.setEnabled(True)

    def _on_ai_models_error(self, msg):
        self._ai_status.setText(i18n.t("Could not fetch the model list: %s") % msg)
        self._ai_load.setEnabled(True)

    def ai_values(self) -> dict:
        return dict(api_key=self._ai_key.text().strip(),
                    model=self._ai_model.currentText().strip(),
                    base_url=self._ai_base.currentText().strip(),
                    ask_first=self._ai_first.isChecked())

    def save_ai_config(self):
        """Write the tab out, if it was touched: a key that came from the
        environment must not land in the file just because OK was pressed."""
        now = self.ai_values()
        if now == self._ai_given:
            return
        ai.save_openrouter_config(now["api_key"], now["model"], now["base_url"],
                                  ask_first=now["ask_first"])
