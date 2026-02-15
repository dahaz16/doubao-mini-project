#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test UUID constraint
"""
import sys
import os
import uuid
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection

def test_insert():
    user_id = "f5577e07-00b5-4394-836b-cd145a453a69" # Existing user
    fake_resp_id = "resp_1234567890abcdef" # Not a UUID
    
    print(f"Testing update with invalid UUID: {fake_resp_id}")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Try to update session_id with non-uuid string
                cursor.execute("""
                    UPDATE narration_status 
                    SET intv_llm_session_id = %s 
                    WHERE user_id = %s
                """, (fake_resp_id, user_id))
                conn.commit()
                print("✅ Update SUCCESS (Unexpected!)")
    except Exception as e:
        print(f"❌ Update FAILED (Expected): {e}")

if __name__ == "__main__":
    test_insert()
