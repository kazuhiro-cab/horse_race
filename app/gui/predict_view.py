from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class PredictView(QWidget):
    def __init__(self):
        super().__init__()
        self.title = QLabel("予想結果")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["券種", "買い目", "推定確率", "オッズ", "EV", "推奨賭け金"])
        self.caution = QLabel("")
        self.caution.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(self.table)
        layout.addWidget(self.caution)
        self.setLayout(layout)

    def show_prediction(self, race_title: str, payload: dict):
        self.title.setText(race_title)
        rows = []
        for market, bets in payload.get("bets", {}).items():
            for b in bets:
                rows.append((market, b["combination"], f"{b['prob']:.2%}", f"{b['odds']:.1f}", f"{b['ev']:.2f}", f"¥{int(b['bet_amount'])}"))

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(value))

        self.caution.setText(payload.get("caution", ""))
