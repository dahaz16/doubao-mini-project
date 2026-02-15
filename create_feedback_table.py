
import logging
from backend.database import get_db_connection, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)

def create_feedback_table():
    """创建一个新的 feedback 表"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Create table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        feedback_id BIGSERIAL PRIMARY KEY,
                        user_id UUID NOT NULL REFERENCES users(user_id),
                        feedback_content TEXT NOT NULL,
                        feedback_voice_url TEXT,
                        created_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """)
                
                # Create index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_user_time ON feedback(user_id, created_time DESC);
                """)
                
                conn.commit()
                logging.info("Successfully created feedback table and index.")
                
    except Exception as e:
        logging.error(f"Failed to create feedback table: {e}")
        raise

if __name__ == "__main__":
    create_feedback_table()
