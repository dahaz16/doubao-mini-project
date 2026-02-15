
import os
import psycopg2
from dotenv import load_dotenv

# Load env variables from .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("Error: DATABASE_URL not found in backend/.env")
    exit(1)

try:
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # Check column names first to be sure
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'feedback'")
    columns = [col[0] for col in cursor.fetchall()]
    print(f"Columns in feedback table: {columns}")

    cursor.execute("SELECT feedback_id, feedback_content, feedback_voice_url, created_time FROM feedback ORDER BY created_time DESC LIMIT 3")
    rows = cursor.fetchall()
    print("\n--- Latest 3 Feedback Entries ---")
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Content: {row[1]}")
        print(f"Voice URL: {row[2]}")
        print(f"Time: {row[3]}")
        print("-" * 20)
        
    conn.close()
except Exception as e:
    print(f"Error connecting to DB: {e}")
