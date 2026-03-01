PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS races (
    race_key TEXT PRIMARY KEY,
    org TEXT NOT NULL,
    date TEXT NOT NULL,
    venue TEXT NOT NULL,
    race_no INTEGER NOT NULL,
    distance_m INTEGER,
    surface TEXT,
    going TEXT,
    field_size INTEGER,
    start_time TEXT,
    grade TEXT,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS entries (
    race_key TEXT NOT NULL,
    horse_key TEXT NOT NULL,
    horse_name TEXT NOT NULL,
    gate INTEGER,
    number INTEGER NOT NULL,
    weight_carried REAL,
    jockey_name TEXT,
    trainer_name TEXT,
    horse_weight_kg REAL,
    horse_weight_diff REAL,
    PRIMARY KEY (race_key, horse_key),
    FOREIGN KEY (race_key) REFERENCES races(race_key)
);

CREATE TABLE IF NOT EXISTS past_performances (
    horse_key TEXT NOT NULL,
    race_date TEXT,
    org TEXT,
    venue TEXT,
    distance_m INTEGER,
    surface TEXT,
    going TEXT,
    finish_pos INTEGER,
    field_size INTEGER,
    time_sec REAL,
    passing TEXT,
    last3f_sec REAL,
    weight_carried REAL,
    jockey_name TEXT,
    class_label TEXT,
    data_missing_flags TEXT
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    race_key TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    market TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (race_key, captured_at, market),
    FOREIGN KEY (race_key) REFERENCES races(race_key)
);

CREATE TABLE IF NOT EXISTS predictions (
    race_key TEXT NOT NULL,
    predicted_at TEXT NOT NULL,
    odds_snapshot_id TEXT,
    market TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (race_key, predicted_at, market),
    FOREIGN KEY (race_key) REFERENCES races(race_key)
);

CREATE TABLE IF NOT EXISTS bankroll_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at TEXT NOT NULL,
    race_key TEXT NOT NULL,
    market TEXT NOT NULL,
    combination TEXT NOT NULL,
    bet_amount REAL NOT NULL,
    odds REAL,
    result TEXT NOT NULL,
    payout REAL,
    bankroll_after REAL
);
