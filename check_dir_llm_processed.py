import sys
import os
import json
from datetime import datetime
from decimal import Decimal

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from backend.database import get_db_connection
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            print("=== Checking Dir LLM (agent='Dir') Records in llm_processed ===")
            
            # Check count
            cursor.execute("""
                SELECT COUNT(*) FROM llm_processed
                WHERE agent = 'Dir'
            """)
            count = cursor.fetchone()[0]
            print(f"Total Dir LLM records in llm_processed: {count}")
            
            if count > 0:
                # Check recent records
                cursor.execute("""
                    SELECT 
                        model_processed_id,
                        user_id,
                        output,
                        agent,
                        created_time
                    FROM llm_processed
                    WHERE agent = 'Dir'
                    ORDER BY created_time DESC
                    LIMIT 5
                """)
                rows = cursor.fetchall()
                print(f"\nFound {len(rows)} recent records:")
                for row in rows:
                    print(f"ID: {row[0]}")
                    print(f"Content: {row[2][:50] if row[2] else 'None'}...")
                    print(f"Time: {row[4]}")
                    print("-" * 40)
            else:
                print("❌ No Dir LLM records found in llm_processed.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
