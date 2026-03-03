from __future__ import annotations

import logging
import traceback
import sys
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMessageBox, QTabWidget

from app import db
from app.gui.backtest_view import BacktestView
from app.gui.predict_view import PredictView
from app.gui.race_list_view import RaceListView
from app.gui.scheduler_view import SchedulerView
from app.gui.settings_view import SettingsView
from app.pipeline.backtest import run_backtest
from app.pipeline.predict import predict_race


@dataclass
class TaskPayload:
    kind: str
    data: object


class Worker(QObject):
    progressed = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self._kwargs["progress_callback"] = self.progressed.emit
            out = self._fn(*self._args, **self._kwargs)
            self.succeeded.emit(out)
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._threads: list[QThread] = []
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

        self._status_label = QLabel("待機中")
        self.statusBar().addPermanentWidget(self._status_label)

        self.race_list.race_selected.connect(self._predict_selected_race)
        self.race_list.run_auto_prediction.connect(self._run_auto_prediction)
        self.race_list.refresh_requested.connect(self._load_races_async)
        self.backtest_view.run_requested.connect(self._run_backtest_async)
        self.settings_view.reset_db_requested.connect(self._reset_database)

        self.settings_view._save()
        QTimer.singleShot(0, self._load_races_async)

    def _set_status(self, text: str):
        self._status_label.setText(text)

    def _run_worker(self, fn, *args, on_success=None, on_fail_title="処理失敗", done_text="完了", **kwargs):
        thread = QThread(self)
        worker = Worker(fn, *args, **kwargs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progressed.connect(self._set_status)
        failed = {"value": False}

        if on_success is not None:
            worker.succeeded.connect(on_success)

        def _on_fail(msg: str):
            failed["value"] = True
            self._logger.error(msg)
            self._set_status(f"エラー: {on_fail_title}")
            QMessageBox.critical(self, on_fail_title, msg.splitlines()[-1] if msg else on_fail_title)

        worker.failed.connect(_on_fail)

        def _finish():
            if not failed["value"]:
                self._set_status(done_text)
            thread.quit()
            thread.wait()
            try:
                self._threads.remove(thread)
            except ValueError:
                pass

        worker.finished.connect(_finish)
        self._threads.append(thread)
        thread.start()

    def _load_races_async(self):
        self._set_status("レース情報取得中...")
        self._run_worker(
            self.race_list.load_races,
            on_success=lambda _: None,
            on_fail_title="レース情報取得失敗",
            done_text="取得完了",
        )

    def _predict_selected_race(self, race: dict):
        settings = self.settings_view.get_settings()
        race_name = f"{race['venue']} {race['race_no']}R"
        self._set_status(f"予想計算中...（{race_name}）")

        def _ok(payload):
            self.predict_view.show_prediction(f"{race['venue']} {race['race_no']}R 予想", payload)
            self.tabs.setCurrentWidget(self.predict_view)

        self._run_worker(
            predict_race,
            race["race_key"],
            settings.odds_mode,
            settings.bankroll,
            on_success=_ok,
            on_fail_title="予想失敗",
            done_text="完了",
        )

    def _run_auto_prediction(self):
        for race in list(self.race_list._races):
            self._predict_selected_race(race)

    def _run_backtest_async(self, from_date: str, to_date: str, market: str):
        self._set_status("バックテスト実行中...（0/0）")

        def _ok(stats):
            self.backtest_view.show_result(stats)

        self._run_worker(run_backtest, from_date, to_date, market, on_success=_ok, on_fail_title="バックテスト失敗", done_text="完了")

    def _reset_database(self):
        try:
            db.reset_db()
        except Exception:
            self._logger.exception("Failed to reset database")
            QMessageBox.critical(self, "DB初期化失敗", "データベース初期化に失敗しました。ログを確認してください。")
            return
        self.settings_view._save()
        QTimer.singleShot(0, self._load_races_async)
        QMessageBox.information(self, "DB初期化", "データベースを初期化しました。")


def run():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run()
