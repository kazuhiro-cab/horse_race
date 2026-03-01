from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QPushButton, QVBoxLayout, QWidget


@dataclass
class AppSettings:
    bankroll: float = 10000.0
    odds_mode: str = "前日最終"
    org: str = "全主催"
    market: str = "全券種"
    offline_mode: bool = False


class SettingsView(QWidget):
    reset_db_requested = Signal()
    def __init__(self):
        super().__init__()
        self._settings = AppSettings()

        self.bankroll = QDoubleSpinBox()
        self.bankroll.setRange(1000, 10_000_000)
        self.bankroll.setSingleStep(100)
        self.bankroll.setValue(self._settings.bankroll)

        self.odds_mode = QComboBox()
        self.odds_mode.addItems(["前日最終", "前日発売開始直後", "当日発売開始直後"])

        self.org = QComboBox()
        self.org.addItems(["全主催", "JRA", "地方競馬"])

        self.market = QComboBox()
        self.market.addItems(["全券種", "単勝", "複勝", "枠連", "馬連", "馬単", "ワイド", "三連複", "三連単", "WIN5"])

        self.offline_mode = QCheckBox("オフラインモード（テスト用）")

        form = QFormLayout()
        form.addRow("手持ち資金", self.bankroll)
        form.addRow("オッズモード", self.odds_mode)
        form.addRow("主催", self.org)
        form.addRow("券種", self.market)
        form.addRow("モード", self.offline_mode)

        self.save_btn = QPushButton("設定を保存")
        self.save_btn.clicked.connect(self._save)

        self.reset_db_btn = QPushButton("DB初期化")
        self.reset_db_btn.clicked.connect(self.reset_db_requested.emit)

        box = QGroupBox("設定")
        box.setLayout(form)
        layout = QVBoxLayout()
        layout.addWidget(box)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.reset_db_btn)
        layout.addStretch(1)
        self.setLayout(layout)

    def _save(self):
        self._settings = AppSettings(
            bankroll=self.bankroll.value(),
            odds_mode=self.odds_mode.currentText(),
            org=self.org.currentText(),
            market=self.market.currentText(),
            offline_mode=self.offline_mode.isChecked(),
        )

    def get_settings(self) -> AppSettings:
        return self._settings
