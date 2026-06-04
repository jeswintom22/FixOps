import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect("logs.db", check_same_thread=False)

cursor = conn.cursor()

# Existing logs table
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
    anomaly_score INTEGER
)
""")

# NEW: Week 3 analysis table
cursor.execute("""
CREATE TABLE IF NOT EXISTS analysis_results(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    service TEXT,
    anomaly_score REAL,
    severity TEXT,
    root_cause TEXT,
    suggested_fix TEXT,
    created_at TEXT
)
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
        VALUES(?,?,?,?,?,?,?,?)
    """,
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


# NEW: Save AI analysis
def save_analysis(
    trace_id,
    service,
    anomaly_score,
    severity,
    root_cause,
    suggested_fix
):
    cursor.execute("""
        INSERT INTO analysis_results(
            trace_id,
            service,
            anomaly_score,
            severity,
            root_cause,
            suggested_fix,
            created_at
        )
        VALUES(?,?,?,?,?,?,?)
    """,
    (
        trace_id,
        service,
        anomaly_score,
        severity,
        root_cause,
        suggested_fix,
        datetime.utcnow().isoformat()
    ))

    conn.commit()


# NEW: Get all analysis results
def get_analysis():
    cursor.execute("""
        SELECT *
        FROM analysis_results
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    return rows


# NEW: Get analysis by trace_id
def get_analysis_by_trace_id(trace_id):
    cursor.execute("""
        SELECT *
        FROM analysis_results
        WHERE trace_id = ?
        ORDER BY id DESC
    """, (trace_id,))

    rows = cursor.fetchall()

    return rows