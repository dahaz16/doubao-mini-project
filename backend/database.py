import sqlite3
from datetime import datetime

DB_NAME = "doubao.db"

def init_db():
    """Initializes the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT NOT NULL,
            ai_summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def insert_record(user_input: str, ai_summary: str) -> int:
    """Inserts a new interaction record into the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO records (user_input, ai_summary)
        VALUES (?, ?)
    """, (user_input, ai_summary))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id

def get_records(limit: int = 10):
    """Retrieves the latest records."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM records ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
