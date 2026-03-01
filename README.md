# keiba-predictor v3.1

GUIベースの競馬予想ソフトです。すべての表示・設定・ログ・DB保存値を日本語表記に統一しています。

## 起動手順（Windows）

1. `setup.bat` を初回のみ実行
2. `start.bat` で起動

## 券種（全9種）

- 単勝
- 複勝
- 枠連
- 馬連
- 馬単
- ワイド
- 三連複
- 三連単
- WIN5（JRAのみ・対象レース限定）

## 主要変更

- GUI完全移行（CLI廃止）
- レース一覧は指定日の全場・全Rを取得して競馬場単位でグループ表示
- `pipeline/result.py` を追加し、未確定の `bankroll_log` を結果照合して更新
- バックテスト実行前に未確定レコードの自動結果取得を実行

## 表記ルール（例）

- 主催: `JRA` / `地方競馬`
- 券種: `単勝, 複勝, 枠連, 馬連, 馬単, ワイド, 三連複, 三連単, WIN5`
- オッズモード: `前日最終, 前日発売開始直後, 当日発売開始直後`
- 結果: `的中, ハズレ, 未確定`

## スクレイピング注意

- 規約・法令遵守は利用者責任です。
- `sources/jra.py` は差し替えポイントです。
- 高負荷アクセスを避けるため最小3秒間隔制御を入れています。

## 実装順序（追記）

19. `pipeline/result.py`（レース結果取得・bankroll_log更新）
20. `app/gui/main_window.py`
21. `app/gui/race_list_view.py`
22. `app/gui/predict_view.py`
23. `app/gui/backtest_view.py`
24. `app/gui/settings_view.py`
25. `app/gui/scheduler_view.py`
26. `setup.bat` と `start.bat`
