#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check LLM Processed Logs for duration
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection

def check_llm_logs():
    user_id = "f5577e07-00b5-4394-836b-cd145a453a69"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    created_time,
                    agent,
                    process_duration,
                    total_tokens,
                    completion_tokens,
                    cached_tokens
                FROM llm_processed
                WHERE user_id = %s
                ORDER BY created_time DESC
                LIMIT 5
            """, (user_id,))
            
            print(f"\nRecent LLM Calls for user {user_id}:")
            for row in cursor.fetchall():
                created_time = row[0]
                agent = row[1]
                duration = row[2]
                total_tok = row[3]
                comp_tok = row[4]
                cached = row[5]
                
                print(f"[{created_time}] Agent: {agent} | Duration: {duration}ms ({duration/1000:.2f}s) | Tokens: {total_tok} (Gen: {comp_tok}, Cache: {cached})")

if __name__ == "__main__":
    check_llm_logs()
