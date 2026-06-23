import sqlite3
from pathlib import Path
from config import DB_PATH

def get_conn():
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        initial_points INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS matches(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        home_team TEXT NOT NULL,
        away_team TEXT NOT NULL,
        match_type TEXT DEFAULT 'Normal',
        match_datetime TEXT,
        home_score INTEGER,
        away_score INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS predictions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        match_id INTEGER,
        pred_home INTEGER,
        pred_away INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, match_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS champion_predictions(
        user_id INTEGER UNIQUE,
        team TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS golden_boot_predictions(
        user_id INTEGER UNIQUE,
        player TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    conn.commit()
    conn.close()

def fetch_df(query, params=()):
    import pandas as pd
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute(query, params=()):
    conn = get_conn()
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def fetchone(query, params=()):
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(query, params).fetchone()
    conn.close()
    return row

def fetchall(query, params=()):
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute(query, params).fetchall()
    conn.close()
    return rows

def set_setting(key, value):
    execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))

def get_setting(key):
    row = fetchone("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else ""
