
import sqlite3
import json

db_path = "backend/data/memoir.db"
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, feedback_content, feedback_voice_url, created_time FROM feedback ORDER BY created_time DESC LIMIT 3")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Content: {row[1]}")
        print(f"Voice URL: {row[2]}")
        print(f"Time: {row[3]}")
        print("-" * 20)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
