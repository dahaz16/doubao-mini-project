
import sys
import os
import json
from datetime import datetime

# Add current directory to path so we can import backend modules
sys.path.append(os.getcwd())

from backend.database import get_db_connection

def custom_json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def inspect_wtr_llm():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if table exists first (just to be safe, though we know it should)
                cursor.execute("SELECT to_regclass('public.llm_processed');")
                if not cursor.fetchone()[0]:
                    print("Error: Table 'llm_processed' does not exist in the database.")
                    return

                # Query latest Wtr call
                query = """
                    SELECT 
                        model_processed_id, 
                        created_time, 
                        process_duration, 
                        total_tokens, 
                        prompt_tokens, 
                        completion_tokens, 
                        input, 
                        output 
                    FROM llm_processed 
                    WHERE agent = 'Wtr' 
                    ORDER BY created_time DESC 
                    LIMIT 1
                """
                cursor.execute(query)
                row = cursor.fetchone()
                
                if not row:
                    print("No Wtr LLM calls found in llm_processed.")
                    return
                
                # Unpack row (index assumption based on query)
                result = {
                    "id": row[0],
                    "timestamp": row[1],
                    "duration_ms": row[2],
                    "total_tokens": row[3],
                    "prompt_tokens": row[4],
                    "completion_tokens": row[5],
                    "input": row[6],
                    "output": row[7]
                }
                
                print(f"=== Latest Wtr LLM Call ===")
                print(f"ID: {result['id']}")
                print(f"Time: {result['timestamp']}")
                print(f"Duration: {result['duration_ms']} ms")
                print(f"Tokens: {result['total_tokens']} (Prompt: {result['prompt_tokens']}, Completion: {result['completion_tokens']})")
                print("\n--- INPUT ---")
                print(result['input'])
                print("\n--- OUTPUT ---")
                print(result['output'])
                print("\n===========================")

    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    inspect_wtr_llm()
