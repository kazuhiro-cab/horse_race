from __future__ import annotations

import argparse
from datetime import date

from app import db
from app.config import DEFAULT_BANKROLL, DEFAULT_ODDS_MODE
from app.pipeline.backtest import run_backtest
from app.pipeline.fetch import fetch_for_date, snapshot_odds
from app.pipeline.predict import predict_race


def today() -> str:
    return date.today().isoformat()


def _auto_batch(args):
    db.init_db()
    d = args.date or today()
    races = db.fetch_races(date=d, org=args.org)
    mock_mode = False
    if not races:
        mock_mode = fetch_for_date(d, args.org)
        snapshot_odds(d, mode=args.odds_mode, org=args.org)
        races = db.fetch_races(date=d, org=args.org)
    if mock_mode:
        print("[MOCK MODE]")
    for r in races:
        out = predict_race(r["race_key"], odds_mode=args.odds_mode, bankroll=args.bankroll)
        bets = out.get("bets", {})
        print(f"\n=== {r['venue']} {r['race_no']}R 予想 ===")
        for m in ["PLACE", "TRIO", "TRIFECTA"]:
            top3 = bets.get(m, [])[:3]
            if not top3:
                continue
            print(f"{m} TOP3:")
            for b in top3:
                print(f"  {b['combination']} EV={b['ev']:.2f} 賭け金=¥{int(b['bet_amount'])}")
        print(out.get("caution", ""))


def cmd_list(args):
    d = args.date or today()
    races = db.fetch_races(date=d, org=args.org)
    if not races:
        fetch_for_date(d, args.org)
        snapshot_odds(d, mode=args.odds_mode, org=args.org)
        races = db.fetch_races(date=d, org=args.org)
        print("[MOCK MODE]")
    print(f"\n[{d}] 開催レース")
    for i, r in enumerate(races, start=1):
        print(f"{i:>3} {r['org']:<3} {r['venue']:<4} {r['race_no']}R {r['distance_m']}m/{r['surface']} {r['start_time']} {r['field_size']}頭")
    choice = input("予想するレース番号を入力してください（Enterで全レース）: ").strip()
    targets = races if not choice else [races[int(choice) - 1]]
    for t in targets:
        predict_race(t["race_key"], args.odds_mode, args.bankroll)


def cmd_predict(args):
    out = predict_race(args.race, args.odds_mode, args.bankroll)
    print(out.get("caution", ""))
    if out.get("favorite_trust", {}).get("score", 1.0) < 0.6:
        print(f"1番人気信頼度低: {out['favorite_trust']['score']:.2f} 理由={','.join(out['favorite_trust']['reasons'])}")


def cmd_fetch(args):
    mock_mode = fetch_for_date(args.date or today(), args.org)
    if mock_mode:
        print("[MOCK MODE]")


def cmd_snapshot(args):
    mock_mode = snapshot_odds(args.date or today(), mode=args.mode, org=args.org)
    if mock_mode:
        print("[MOCK MODE]")


def cmd_backtest(args):
    print(run_backtest(args.from_date, args.to_date, args.market))


def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument("--date")
    p.add_argument("--org", default="all")
    p.add_argument("--odds_mode", default=DEFAULT_ODDS_MODE)
    p.add_argument("--market", default="all")
    p.add_argument("--bankroll", type=float, default=DEFAULT_BANKROLL)
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list")
    pr = sub.add_parser("predict")
    pr.add_argument("--race", required=True)

    sub.add_parser("fetch")
    so = sub.add_parser("snapshot_odds")
    so.add_argument("--mode", default=DEFAULT_ODDS_MODE)

    bt = sub.add_parser("backtest")
    bt.add_argument("--from", dest="from_date", required=True)
    bt.add_argument("--to", dest="to_date", required=True)
    bt.add_argument("--market", default="all")

    sub.add_parser("scheduler")
    return p


def main():
    db.init_db()
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd is None:
        _auto_batch(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "predict":
        cmd_predict(args)
    elif args.cmd == "fetch":
        cmd_fetch(args)
    elif args.cmd == "snapshot_odds":
        cmd_snapshot(args)
    elif args.cmd == "backtest":
        cmd_backtest(args)
    elif args.cmd == "scheduler":
        from app.scheduler import run_scheduler
        run_scheduler()


if __name__ == "__main__":
    main()
