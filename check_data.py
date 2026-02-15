
import os
import sys
import logging

# Add backend to path to import database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from backend.database import get_db_connection
except ImportError:
    # Try relative import if running from root
    try:
        from database import get_db_connection
    except ImportError:
        print("Error: Could not import database module. Run from project root.")
        sys.exit(1)

def check_linkage():
    print("Checking linkage between interview_original_text and llm_processed...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 1. Check if related_original_text_id column exists and has values
            cursor.execute("""
                SELECT COUNT(*) 
                FROM llm_processed 
                WHERE related_original_text_id IS NOT NULL
            """)
            linked_count = cursor.fetchone()[0]
            print(f"Records in llm_processed with related_original_text_id: {linked_count}")
            
            # 2. Check a few recent Intv examples
            cursor.execute("""
                SELECT model_processed_id, agent, related_original_text_id, created_time
                FROM llm_processed
                WHERE agent = 'Intv'
                ORDER BY created_time DESC
                LIMIT 5
            """)
            print("\nRecent Intv LLM Logs:")
            for row in cursor.fetchall():
                print(f"  ID: {row[0]}, Agent: {row[1]}, LinkID: {row[2]}, Time: {row[3]}")

            # 3. Check recent AI original texts
            cursor.execute("""
                SELECT interview_original_text_id, speaker_type, created_time, left(original_text, 20)
                FROM interview_original_text
                WHERE speaker_type = 1
                ORDER BY created_time DESC
                LIMIT 5
            """)
            print("\nRecent Intv Original Texts:")
            for row in cursor.fetchall():
                print(f"  ID: {row[0]}, Type: {row[1]}, Time: {row[2]}, Text: {row[3]}...")

if __name__ == "__main__":
    try:
        check_linkage()
    except Exception as e:
        print(f"Error: {e}")
