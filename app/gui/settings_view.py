from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass
class AppSettings:
    bankroll: float = 10000.0
    odds_mode: str = "prevday_last"
    org: str = "all"
    market: str = "all"


class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = AppSettings()

        self.bankroll = QDoubleSpinBox()
        self.bankroll.setRange(1000, 10_000_000)
        self.bankroll.setSingleStep(100)
        self.bankroll.setValue(self._settings.bankroll)

        self.odds_mode = QComboBox()
        self.odds_mode.addItems(["prevday_last", "prevday_open", "dayof_open"])

        self.org = QComboBox()
        self.org.addItems(["all", "JRA", "NAR"])

        self.market = QComboBox()
        self.market.addItems(["all", "PLACE", "TRIO", "TRIFECTA"])

        form = QFormLayout()
        form.addRow("手持ち資金", self.bankroll)
        form.addRow("オッズモード", self.odds_mode)
        form.addRow("主催", self.org)
        form.addRow("券種", self.market)

        self.save_btn = QPushButton("設定を保存")
        self.save_btn.clicked.connect(self._save)

        box = QGroupBox("設定")
        box.setLayout(form)

        layout = QVBoxLayout()
        layout.addWidget(box)
        layout.addWidget(self.save_btn)
        layout.addStretch(1)
        self.setLayout(layout)

    def _save(self):
        self._settings = AppSettings(
            bankroll=self.bankroll.value(),
            odds_mode=self.odds_mode.currentText(),
            org=self.org.currentText(),
            market=self.market.currentText(),
        )

    def get_settings(self) -> AppSettings:
        return self._settings
