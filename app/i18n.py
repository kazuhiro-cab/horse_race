from __future__ import annotations

ORG_EN_TO_JA = {"JRA": "JRA", "NAR": "地方競馬", "all": "全主催"}
ORG_JA_TO_EN = {v: k for k, v in ORG_EN_TO_JA.items()}
ORG_JA_TO_EN["地方競馬"] = "NAR"

MARKET_EN_TO_JA = {
    "WIN": "単勝",
    "PLACE": "複勝",
    "BRACKET": "枠連",
    "EXACTA": "馬連",
    "QUINELLA": "馬単",
    "WIDE": "ワイド",
    "TRIO": "三連複",
    "TRIFECTA": "三連単",
    "WIN5": "WIN5",
    "all": "全券種",
}
MARKET_JA_TO_EN = {v: k for k, v in MARKET_EN_TO_JA.items()}

ODDS_MODE_EN_TO_JA = {
    "prevday_last": "前日最終",
    "prevday_open": "前日発売開始直後",
    "dayof_open": "当日発売開始直後",
}
ODDS_MODE_JA_TO_EN = {v: k for k, v in ODDS_MODE_EN_TO_JA.items()}

SURFACE_EN_TO_JA = {"TURF": "芝", "DIRT": "ダート", "JUMP": "障害"}
GOING_EN_TO_JA = {"FIRM": "良", "GOOD": "稍重", "YIELDING": "重", "SOFT": "不良", "HEAVY": "不良"}
RESULT_EN_TO_JA = {"WIN": "的中", "LOSE": "ハズレ", "PENDING": "未確定"}


def org_to_ja(v: str) -> str:
    return ORG_EN_TO_JA.get(v, v)


def org_to_en(v: str) -> str:
    return ORG_JA_TO_EN.get(v, v)


def market_to_ja(v: str) -> str:
    return MARKET_EN_TO_JA.get(v, v)


def market_to_en(v: str) -> str:
    return MARKET_JA_TO_EN.get(v, v)


def odds_mode_to_ja(v: str) -> str:
    return ODDS_MODE_EN_TO_JA.get(v, v)


def odds_mode_to_en(v: str) -> str:
    return ODDS_MODE_JA_TO_EN.get(v, v)


def result_to_ja(v: str) -> str:
    return RESULT_EN_TO_JA.get(v, v)
