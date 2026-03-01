from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
LOG_DIR = DATA_DIR / "logs"
SAMPLES_DIR = DATA_DIR / "samples"
DB_PATH = DB_DIR / "keiba.sqlite3"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

SOURCE = "jra"
DEFAULT_ORG = "all"
DEFAULT_ODDS_MODE = "prevday_last"
DEFAULT_MARKET = "all"
DEFAULT_BANKROLL = 10000.0
REQUEST_INTERVAL_SEC = 3

MIN_BET_YEN = 100
MAX_BET_RATIO_PER_TICKET = 0.20
MAX_BET_RATIO_PER_RACE = 0.30
RANDOM_SEED = 42

DEFAULT_OFFLINE_MODE = False
