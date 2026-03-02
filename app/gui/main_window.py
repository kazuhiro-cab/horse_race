from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget

from app import db
from app.gui.backtest_view import BacktestView
from app.gui.predict_view import PredictView
from app.gui.race_list_view import RaceListView
from app.gui.scheduler_view import SchedulerView
from app.gui.settings_view import SettingsView
from app.pipeline.predict import predict_race


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keiba Predictor v3.1")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.race_list = RaceListView()
        self.predict_view = PredictView()
        self.backtest_view = BacktestView()
        self.settings_view = SettingsView()
        self.scheduler_view = SchedulerView()

        self.tabs.addTab(self.race_list, "レース一覧")
        self.tabs.addTab(self.predict_view, "予想")
        self.tabs.addTab(self.backtest_view, "バックテスト")
        self.tabs.addTab(self.settings_view, "設定")
        self.tabs.addTab(self.scheduler_view, "スケジューラ")
        self.setCentralWidget(self.tabs)

        self.race_list.race_selected.connect(self._predict_selected_race)
        self.race_list.run_auto_prediction.connect(self._run_auto_prediction)
        self.settings_view.reset_db_requested.connect(self._reset_database)

        self.settings_view._save()
        self._load_races_or_stop()

    def _load_races_or_stop(self):
        try:
            self.race_list.load_races()
        except Exception:
            QMessageBox.critical(self, "取得失敗", "実データの取得に失敗しました。ネットワーク接続を確認してください")

    def _predict_selected_race(self, race: dict):
        settings = self.settings_view.get_settings()
        payload = predict_race(race["race_key"], settings.odds_mode, settings.bankroll)
        title = f"{race['venue']} {race['race_no']}R 予想"
        self.predict_view.show_prediction(title, payload)
        self.tabs.setCurrentWidget(self.predict_view)

    def _run_auto_prediction(self):
        for i in range(self.race_list.table.rowCount()):
            race = self.race_list._races[i]
            self._predict_selected_race(race)

    def _reset_database(self):
        db.reset_db()
        self.settings_view._save()
        self._load_races_or_stop()
        QMessageBox.information(self, "DB初期化", "データベースを初期化しました。")


def run():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run()
