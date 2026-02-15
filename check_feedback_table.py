import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from backend.database import get_db_connection
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("SELECT to_regclass('public.feedback');")
            exists = cursor.fetchone()[0]
            print(f"Table 'feedback' exists: {exists}")
            
            if exists:
                # Check columns
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'feedback';
                """)
                columns = cursor.fetchall()
                print("Columns:")
                for col in columns:
                    print(f" - {col[0]}: {col[1]}")
            else:
                print("Creating table 'feedback'...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        feedback_id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        feedback_content TEXT,
                        feedback_voice_url TEXT,
                        created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
                print("Table 'feedback' created.")

except Exception as e:
    print(f"Error: {e}")
