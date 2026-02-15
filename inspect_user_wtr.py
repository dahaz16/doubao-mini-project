
import sys
import os
import json
from datetime import datetime

# Add current directory to path so we can import backend modules
sys.path.append(os.getcwd())

from backend.database import get_db_connection

def inspect_wtr_llm_for_user(user_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Query latest Wtr call for specific user
                query = """
                    SELECT 
                        model_processed_id, 
                        created_time, 
                        input, 
                        output 
                    FROM llm_processed 
                    WHERE agent = 'Wtr' AND user_id = %s
                    ORDER BY created_time DESC 
                    LIMIT 1
                """
                cursor.execute(query, (user_id,))
                row = cursor.fetchone()
                
                if not row:
                    print(f"No Wtr LLM calls found for user {user_id}.")
                    return
                
                # Unpack row
                result = {
                    "id": row[0],
                    "timestamp": row[1],
                    "input": row[2],
                    "output": row[3]
                }
                
                print(f"=== Wtr LLM Call for User {user_id} ===")
                print(f"Time: {result['timestamp']}")
                print("\n--- INPUT ---")
                print(result['input'])
                print("\n--- OUTPUT ---")
                print(result['output'])
                print("\n===========================")

    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    target_user_id = "f5577e07-00b5-4394-836b-cd145a453a69"
    inspect_wtr_llm_for_user(target_user_id)
