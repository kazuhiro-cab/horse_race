from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.pipeline.backtest import run_backtest


class BacktestView(QWidget):
    def __init__(self):
        super().__init__()
        self.from_date = QDateEdit()
        self.from_date.setDate(date.today() - timedelta(days=30))
        self.from_date.setCalendarPopup(True)
        self.to_date = QDateEdit()
        self.to_date.setDate(date.today())
        self.to_date.setCalendarPopup(True)
        self.run_btn = QPushButton("実行")
        self.run_btn.clicked.connect(self.run_backtest)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["指標", "値"])

        self.chart = QChart()
        self.chart_view = QChartView(self.chart)

        top = QHBoxLayout()
        top.addWidget(self.from_date)
        top.addWidget(self.to_date)
        top.addWidget(self.run_btn)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.chart_view)
        self.setLayout(layout)

    def run_backtest(self):
        stats = run_backtest(
            self.from_date.date().toString("yyyy-MM-dd"),
            self.to_date.date().toString("yyyy-MM-dd"),
            "all",
            use_mock=False,
        )
        keys = ["的中率", "回収率", "EV推定精度", "1番人気信頼度スコア精度", "凡走リスクスコア精度"]
        self.table.setRowCount(len(keys))
        for i, k in enumerate(keys):
            self.table.setItem(i, 0, QTableWidgetItem(k))
            self.table.setItem(i, 1, QTableWidgetItem(f"{stats.get(k, 0):.4f}"))

        series = QLineSeries()
        csv_path = stats.get("資金推移CSV")
        if csv_path:
            with open(csv_path, encoding="utf-8") as f:
                next(f)
                for line in f:
                    idx, value = line.strip().split(",")
                    series.append(float(idx), float(value))
        chart = QChart()
        chart.addSeries(series)
        axis_x = QValueAxis()
        axis_x.setTitleText("取引回数")
        axis_y = QValueAxis()
        axis_y.setTitleText("資金")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        chart.setTitle("資金推移")
        self.chart_view.setChart(chart)
