import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect("logs.db", check_same_thread=False)

cursor = conn.cursor()

# Logs table
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

# AI Analysis table
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

# Week 4 Action History table
cursor.execute("""
CREATE TABLE IF NOT EXISTS action_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    service TEXT,
    severity TEXT,
    action_type TEXT,
    status TEXT,
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


def get_analysis():
    cursor.execute("""
        SELECT *
        FROM analysis_results
        ORDER BY id DESC
    """)

    return cursor.fetchall()


def get_analysis_by_trace_id(trace_id):
    cursor.execute("""
        SELECT *
        FROM analysis_results
        WHERE trace_id = ?
        ORDER BY id DESC
    """, (trace_id,))

    return cursor.fetchall()


# Week 4 Action History Functions

def save_action(
    trace_id,
    service,
    severity,
    action_type,
    status="completed"
):
    cursor.execute("""
        INSERT INTO action_history(
            trace_id,
            service,
            severity,
            action_type,
            status,
            created_at
        )
        VALUES(?,?,?,?,?,?)
    """,
    (
        trace_id,
        service,
        severity,
        action_type,
        status,
        datetime.utcnow().isoformat()
    ))

    conn.commit()


def get_actions():
    cursor.execute("""
        SELECT *
        FROM action_history
        ORDER BY id DESC
    """)

    return cursor.fetchall()


def get_actions_by_trace_id(trace_id):
    cursor.execute("""
        SELECT *
        FROM action_history
        WHERE trace_id = ?
        ORDER BY id DESC
    """, (trace_id,))

    return cursor.fetchall()