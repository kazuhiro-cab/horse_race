from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class SchedulerView(QWidget):
    def __init__(self):
        super().__init__()
        self.running = False
        self.status = QLabel("停止中")
        self.next_run = QLabel("次回実行時刻: -")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.start_btn = QPushButton("起動")
        self.stop_btn = QPushButton("停止")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)

        self.timer = QTimer()
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self._tick)

        layout = QVBoxLayout()
        layout.addWidget(self.status)
        layout.addWidget(self.next_run)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.log)
        self.setLayout(layout)

    def start(self):
        self.running = True
        self.status.setText("稼働中")
        self.log.append("スケジューラを起動しました")
        self.timer.start()

    def stop(self):
        self.running = False
        self.status.setText("停止中")
        self.log.append("スケジューラを停止しました")
        self.timer.stop()

    def _tick(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.next_run.setText(f"次回実行時刻: {ts} + schedule")
        self.log.append(f"[{ts}] 稼働確認")
