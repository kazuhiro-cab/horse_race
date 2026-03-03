from __future__ import annotations

from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDateEdit, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app import db
from app.i18n import org_to_en
from app.pipeline.fetch import fetch_for_date, snapshot_odds


class RaceListView(QWidget):
    race_selected = Signal(dict)
    run_auto_prediction = Signal()
    refresh_requested = Signal()

    def __init__(self):
        super().__init__()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())

        self.org = QComboBox()
        self.org.addItems(["全主催", "JRA", "地方競馬"])

        self.refresh_btn = QPushButton("レース一覧更新")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.auto_btn = QPushButton("全自動予想")
        self.auto_btn.clicked.connect(self.run_auto_prediction.emit)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["主催", "競馬場", "グループ", "R", "距離", "馬場", "発走", "頭数"])
        self.table.cellClicked.connect(self._on_click)

        top = QHBoxLayout()
        top.addWidget(self.date_edit)
        top.addWidget(self.org)
        top.addWidget(self.refresh_btn)
        top.addWidget(self.auto_btn)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self._races: list[dict] = []

    def _selected_date(self) -> str:
        return self.date_edit.date().toString("yyyy-MM-dd")

    def _looks_incomplete(self, races: list[dict]) -> bool:
        if not races:
            return True
        by_group: dict[tuple[str, str], set[int]] = {}
        for r in races:
            by_group.setdefault((r["org"], r["venue"]), set()).add(int(r["race_no"]))
        return any(len(v) < 12 for v in by_group.values())

    def load_races(self, progress_callback=None):
        d = self._selected_date()
        org = self.org.currentText()
        db.init_db()
        races = db.fetch_races(date=d, org=org)
        if self._looks_incomplete(races):
            fetch_for_date(d, org_to_en(org), progress_callback=progress_callback)
            snapshot_odds(d, mode="前日最終", org=org)
            races = db.fetch_races(date=d, org=org)

        races = sorted(races, key=lambda r: (r["org"], r["venue"], r["race_no"]))
        self._races = races
        self.table.setRowCount(len(races))
        if not races:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("データなし（取得失敗またはレースなし）"))
            return
        current_group = ""
        for i, r in enumerate(races):
            group = f"{r['org']}:{r['venue']}"
            group_text = group if group != current_group else ""
            current_group = group
            vals = [
                r["org"],
                r["venue"],
                group_text,
                f"{r['race_no']}R",
                str(r.get("distance_m") or ""),
                r.get("surface") or "",
                r.get("start_time") or "",
                f"{r.get('field_size') or ''}",
            ]
            for c, v in enumerate(vals):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _on_click(self, row: int, _column: int):
        if 0 <= row < len(self._races):
            self.race_selected.emit(self._races[row])
