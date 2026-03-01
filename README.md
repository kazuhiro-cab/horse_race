# keiba-predictor

自動取得データ駆動・入力最小・トータルプラス志向の競馬予想CLIです。

## セットアップ

```bash
pip install -r requirements.txt
python -m app fetch --date 2026-03-01 --org all
python -m app snapshot_odds --date 2026-03-01 --mode prevday_last
python -m app
```

Playwright実データ取得を有効にする場合:

```bash
pip install playwright
playwright install chromium
```

## コマンド

- `python -m app` : 全自動バッチモード
- `python -m app list [--date DATE] [--org ORG]`
- `python -m app predict --race RACE_KEY [--odds_mode MODE] [--bankroll AMOUNT]`
- `python -m app fetch [--date DATE] [--org ORG]`
- `python -m app snapshot_odds [--date DATE] [--mode MODE]`
- `python -m app backtest --from DATE --to DATE [--market MARKET]`
- `python -m app scheduler`

## スクレイピングと規約上の注意

- JRA公式サイト利用規約（2026年3月時点）には自動取得を明示的に禁止する条項は確認できませんでしたが、規約は更新され得るため利用者が最新規約を確認してください。
- 過度なアクセスを避けるため、`sources/jra.py` では最低3秒の間隔制御を入れています。
- 仕様変更で取得不能になった場合は `sources/jra.py` を修正してください。
- JRA/NAR の取得方法は各主催者の利用規約に依存します。合法かつ規約に適合した手段を利用者が選択してください。
- 公式フォーマット変更時は `sources/jra.py` / `sources/nar.py` の差し替えで対応する設計です。

## EV表示の注意文

本ソフトのEV表示には以下を必ず添付します。

```text
[注意] このEVは {captured_at} 時点のオッズを基準にした評価値です。
       当日のオッズは変動するため、実際のEVは異なります。
       EV > 1.0 は長期的な期待値の優位性を示すものであり、
       個別レースの的中を保証するものではありません。
```

## DataLab移行手順

1. `pip install pywin32`
2. `sources/jra_datalab.py` を作成して `BaseSource` を実装
3. `config.py` の `SOURCE` を `jra_datalab` に変更
4. `features/build.py` に上がり3F・通過順・調教特徴量を追加
5. モデル再学習

## 免責事項

- 本ソフトは投資判断補助を目的としており、利益を保証しません。
- EV>1.0 は長期期待値の優位性を示す指標であり、単一レースの的中保証ではありません。
