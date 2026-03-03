# WORKLOG.md — keiba-predictor 作業ログ

## 現在の状態

Codexによる修正指示（6点）を送付済みである。修正の実装結果はまだ確認していない。  
DB初期化後にJRAデータ取得が失敗し、レース一覧・予想・バックテストの全機能が停止している状態である。

---

## 解決済み課題

- MockSourceがデフォルトのデータソースとして混入しており、架空データを実データとして表示・バックテストに使用していた問題を特定済み。現バージョン（v3.1）ではfetch.pyからMockSourceへの参照を除去済み。

---

## 現在の課題

### 課題1：JRAデータ取得の失敗が無音終了する
- `app/sources/jra.py` の `fetch_race_list()` が例外発生時に `except Exception: return []` で空リストを返す。
- UIには「完了」と表示され、エラー発生をユーザーが認識できない。

### 課題2：アクセス先URLがUIに表示されない
- `app/sources/jra.py` 内の `page.goto()` 呼び出し前後で `progress_callback` が一部しか呼ばれていない。
- ステータスバーに「レース情報取得中」と表示されるが、どのURLにアクセスしているかが不明である。

### 課題3：DB初期化後に全機能が停止する
- `load_races()` がfetch失敗で空を返すと、DBにデータが入らないままUIの全機能が停止する。
- テーブルに「データなし」等のフィードバックが表示されない。

---

## Codexへの修正指示（送付済み・実装未確認）

以下の6点の修正をCodexに指示済みである。

1. `app/sources/jra.py` — `fetch_race_list()` の exceptブロックで例外を再送出する
2. `app/sources/nar.py` — 同様に例外を再送出する
3. `app/pipeline/fetch.py` — `progress_callback` でアクセス開始通知を追加する
4. `app/gui/main_window.py` — 取得失敗時のエラーダイアログ表示を明示する
5. `app/sources/jra.py` — 全 `page.goto()` 直前に `progress_callback` でURL表示を追加する
6. `app/gui/race_list_view.py` — fetch失敗後にテーブルへ「データなし（取得失敗またはレースなし）」を明示する

---

## 次のアクション候補

- Codexが適用した修正コードをレビューする
- `start_error.log` または `data/logs/app_error.log` の内容を確認して実際の例外を特定する
- playwrightのインストール状態を確認する（`playwright install chromium` の実行要否を判断する）

---

## 作業方針（不変）

- 実データ（JRA/NAR）のみを使用する。MockSourceへのフォールバックは採用しない。
- エラーはUIに明示表示する。無音終了・隠蔽は採用しない。
- アクセス中のURLはステータスバーにリアルタイム表示する。
- 修正はCodexへの指示形式（コードブロック）で出力する。

---

## Claudeへの引き継ぎ指示文（次回ルーム冒頭に貼り付ける）

```
以下のリポジトリをgit cloneして、WORKLOG.mdを読んだ上で作業を開始してほしい。
https://github.com/kazuhiro-cab/horse_race

WORKLOG.mdに現在の課題・解決済み課題・作業方針が記載されている。
内容を確認した上で、現在の課題に対する対処方針を提示してほしい。
```
