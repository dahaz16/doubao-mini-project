#!/usr/bin/env python3
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host='sh-cynosdbmysql-grp-3bi5yw3m.sql.tencentcdb.com',
    port=21133,
    user='root',
    password='Wyt20050527',
    database='memoir_db'
)

cursor = conn.cursor()

# 检查最近的音频记录
print("=== 最近10条音频记录 ===")
cursor.execute("""
    SELECT id, user_id, speaker_type, audio_url, created_at 
    FROM original_voice 
    ORDER BY created_at DESC 
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"ID: {row[0]}, User: {row[1][:8]}..., Speaker: {row[2]}, URL: {row[3]}, Time: {row[4]}")

print("\n=== 音频URL统计 ===")
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN audio_url IS NOT NULL AND audio_url != '' THEN 1 ELSE 0 END) as with_url,
        SUM(CASE WHEN audio_url IS NULL OR audio_url = '' THEN 1 ELSE 0 END) as without_url
    FROM original_voice
""")

stats = cursor.fetchone()
print(f"总记录数: {stats[0]}")
print(f"有URL: {stats[1]}")
print(f"无URL: {stats[2]}")

cursor.close()
conn.close()
