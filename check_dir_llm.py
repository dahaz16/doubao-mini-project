import sys
import os
import json
from datetime import datetime
from decimal import Decimal

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DateTimeEncoder, self).default(obj)

try:
    from backend.database import get_db_connection
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            print("=== Checking Dir LLM (speaker_type=3) Records ===")
            
            # Check count
            cursor.execute("""
                SELECT COUNT(*) FROM interview_original_text
                WHERE speaker_type = 3
            """)
            count = cursor.fetchone()[0]
            print(f"Total Dir LLM records: {count}")
            
            if count > 0:
                # Check recent records
                cursor.execute("""
                    SELECT 
                        interview_original_text_id,
                        user_id,
                        original_text,
                        created_time
                    FROM interview_original_text
                    WHERE speaker_type = 3
                    ORDER BY created_time DESC
                    LIMIT 5
                """)
                rows = cursor.fetchall()
                print(f"\nFound {len(rows)} recent records:")
                for row in rows:
                    print(f"ID: {row[0]}")
                    print(f"Content: {row[2][:50]}...")
                    print(f"Time: {row[3]}")
                    print("-" * 40)
            else:
                print("❌ No Dir LLM records found in database.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
