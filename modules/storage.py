"""Local SQLite storage for settings, activity events, metric snapshots and demo alerts."""
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timezone

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "snakbite.db"

DEFAULT_SETTINGS = {
    "cpu_warning": 80, "cpu_critical": 90,
    "ram_warning": 80, "ram_critical": 90,
    "disk_warning": 80, "disk_critical": 90,
    "refresh_seconds": 30,
}

def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    return con

def initialize():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
          event_type TEXT NOT NULL, severity TEXT NOT NULL, description TEXT NOT NULL,
          metrics TEXT, result TEXT, alert_status TEXT, source TEXT NOT NULL DEFAULT 'REAL'
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS demo_alert (
          id INTEGER PRIMARY KEY CHECK(id=1), status TEXT NOT NULL,
          updated_at TEXT NOT NULL, history TEXT NOT NULL
        );
        """)
        for key, value in DEFAULT_SETTINGS.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, json.dumps(value)))
        con.execute("INSERT OR IGNORE INTO demo_alert(id,status,updated_at,history) VALUES(1,'Open',?,'[]')", (now(),))

def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def add_event(event_type, severity, description, metrics=None, result=None, alert_status=None, source="REAL"):
    with connect() as con:
        con.execute("INSERT INTO events(timestamp,event_type,severity,description,metrics,result,alert_status,source) VALUES(?,?,?,?,?,?,?,?)",
                    (now(), event_type, severity, description, json.dumps(metrics or {}), result, alert_status, source))

def get_events(limit=500):
    with connect() as con:
        rows = con.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]

def clear_events():
    with connect() as con:
        con.execute("DELETE FROM events")

def get_settings():
    with connect() as con:
        result = DEFAULT_SETTINGS.copy()
        for row in con.execute("SELECT key,value FROM settings"):
            try: result[row["key"]] = json.loads(row["value"])
            except (ValueError, TypeError): pass
    return result

def save_settings(settings):
    with connect() as con:
        con.executemany("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        [(k, json.dumps(v)) for k,v in settings.items()])

def get_demo_alert():
    with connect() as con:
        row = con.execute("SELECT * FROM demo_alert WHERE id=1").fetchone()
    return dict(row)

def update_demo_alert(status):
    stamp = now()
    with connect() as con:
        row = con.execute("SELECT history FROM demo_alert WHERE id=1").fetchone()
        history = json.loads(row[0]) if row else []
        history.append({"timestamp": stamp, "status": status})
        con.execute("UPDATE demo_alert SET status=?,updated_at=?,history=? WHERE id=1", (status,stamp,json.dumps(history)))
    add_event("Demo alert action", "Info", f"Simulated alert marked {status.lower()}.", result=status, alert_status=status, source="DEMO")

def reset_demo_alert():
    with connect() as con:
        con.execute("UPDATE demo_alert SET status='Open',updated_at=?,history='[]' WHERE id=1", (now(),))
    add_event("Demo reset", "Info", "Simulated demo alert reset to Open.", result="Open", alert_status="Open", source="DEMO")
