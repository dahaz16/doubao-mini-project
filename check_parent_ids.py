#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时脚本:检查 parent_id 数据"""

import sys
sys.path.insert(0, 'backend')

from database import get_db_connection

def check_parent_ids():
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print('=== Topic 表最新 10 条记录 ===')
        cur.execute('''
            SELECT topic_id, topic_title, parent_stage_id, created_time 
            FROM topic 
            ORDER BY created_time DESC 
            LIMIT 10;
        ''')
        for row in cur.fetchall():
            print(f'ID: {row[0]}, Title: {row[1]}, Parent Stage ID: {row[2]}, Time: {row[3]}')
        
        print('\n=== Shot 表最新 10 条记录 ===')
        cur.execute('''
            SELECT shot_id, shot_title, parent_topic_id, created_time 
            FROM shot 
            ORDER BY created_time DESC 
            LIMIT 10;
        ''')
        for row in cur.fetchall():
            print(f'ID: {row[0]}, Title: {row[1]}, Parent Topic ID: {row[2]}, Time: {row[3]}')
        
        print('\n=== Stage 表最新 10 条记录 ===')
        cur.execute('''
            SELECT stage_id, stage_title, created_time 
            FROM stage 
            ORDER BY created_time DESC 
            LIMIT 10;
        ''')
        for row in cur.fetchall():
            print(f'ID: {row[0]}, Title: {row[1]}, Time: {row[2]}')
        
        print('\n=== Storyboard 最新 20 条记录 ===')
        cur.execute('''
            SELECT story_id, story_type, entity_id, story_content, created_time 
            FROM storyboard 
            ORDER BY created_time DESC 
            LIMIT 20;
        ''')
        for row in cur.fetchall():
            type_name = {1: 'Stage', 2: 'Topic', 3: 'Shot', 4: 'Character'}.get(row[1], 'Unknown')
            print(f'ID: {row[0]}, Type: {type_name}, Entity ID: {row[2]}, Content: {row[3][:50]}..., Time: {row[4]}')
        
        cur.close()

if __name__ == '__main__':
    check_parent_ids()
