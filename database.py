import sqlite3
import json

conn = sqlite3.connect("logs.db",check_same_thread=False)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               timestamp TEXT,
               level TEXT,
               service TEXT,
               message TEXT,
               trace_id TEXT,
               metadata TEXT,
               event_type TEXT,
               anomaly_score INTEGER)
               """)

conn.commit()

def save_log(log):
    cursor.execute("""
            INSERT INTO logs(
                  timestamp,
                   level,
                   service,
                   message,
                   trace_id,
                   metadata,
                   event_type,
                   anomaly_score
                   )
                   VALUES(?,?,?,?,?,?,?,?)""",
                   (
                    log["timestamp"],
                    log["level"],
                    log["service"],
                    log["message"],
                    log["trace_id"],
                    json.dumps(log["metadata"]),
                    log["event_type"],
                    log["anomaly_score"]
                   ))
    conn.commit()