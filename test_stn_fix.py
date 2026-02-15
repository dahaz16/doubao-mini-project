#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化测试：直接测试数据库插入和更新函数
"""
import sys
import os

# 直接测试数据库函数
from backend.database import get_db_connection

def test_insert_with_null_fk():
    """测试插入时外键为 NULL"""
    print("=" * 60)
    print("测试两阶段处理：插入实体（外键为 NULL）")
    print("=" * 60)
    
    user_id = "f5577e07-00b5-4394-836b-cd145a453a69"
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. 插入 Topic（parent_stage_id = NULL）
                print("\n[1] 插入 Topic（parent_stage_id = NULL）...")
                cur.execute("""
                    INSERT INTO topic (user_id, parent_stage_id, topic_title, topic_summary, topic_content)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING topic_id
                """, (user_id, None, "测试话题", "测试摘要", "测试内容"))
                topic_id = cur.fetchone()[0]
                print(f"✅ Topic 插入成功，ID: {topic_id}")
                
                # 2. 插入 Shot（parent_topic_id = NULL）
                print("\n[2] 插入 Shot（parent_topic_id = NULL）...")
                cur.execute("""
                    INSERT INTO shot (user_id, parent_topic_id, shot_title, shot_summary, shot_content, shot_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING shot_id
                """, (user_id, None, "测试镜头", "测试摘要", "测试内容", 1))
                shot_id = cur.fetchone()[0]
                print(f"✅ Shot 插入成功，ID: {shot_id}")
                
                # 3. 插入 Character（related_shot_id = NULL）
                print("\n[3] 插入 Character（related_shot_id = NULL）...")
                cur.execute("""
                    INSERT INTO character (user_id, related_shot_id, name, relation, evaluation)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING character_id
                """, (user_id, None, "测试人物", "测试关系", "测试评价"))
                char_id = cur.fetchone()[0]
                print(f"✅ Character 插入成功，ID: {char_id}")
                
                # 4. 更新 Topic 的 parent_stage_id
                print("\n[4] 更新 Topic 的 parent_stage_id = 8...")
                cur.execute("""
                    UPDATE topic SET parent_stage_id = %s WHERE topic_id = %s
                """, (8, topic_id))
                print(f"✅ Topic 父级关系建立成功")
                
                # 5. 更新 Shot 的 parent_topic_id
                print("\n[5] 更新 Shot 的 parent_topic_id = {topic_id}...")
                cur.execute("""
                    UPDATE shot SET parent_topic_id = %s WHERE shot_id = %s
                """, (topic_id, shot_id))
                print(f"✅ Shot 父级关系建立成功")
                
                # 6. 更新 Character 的 related_shot_id
                print("\n[6] 更新 Character 的 related_shot_id = {shot_id}...")
                cur.execute("""
                    UPDATE character SET related_shot_id = %s WHERE character_id = %s
                """, (shot_id, char_id))
                print(f"✅ Character 关联关系建立成功")
                
                conn.commit()
                
                # 7. 验证结果
                print("\n[7] 验证结果...")
                cur.execute("SELECT parent_stage_id FROM topic WHERE topic_id = %s", (topic_id,))
                result = cur.fetchone()[0]
                assert result == 8, f"Topic parent_stage_id 错误: {result}"
                print(f"✅ Topic.parent_stage_id = {result}")
                
                cur.execute("SELECT parent_topic_id FROM shot WHERE shot_id = %s", (shot_id,))
                result = cur.fetchone()[0]
                assert result == topic_id, f"Shot parent_topic_id 错误: {result}"
                print(f"✅ Shot.parent_topic_id = {result}")
                
                cur.execute("SELECT related_shot_id FROM character WHERE character_id = %s", (char_id,))
                result = cur.fetchone()[0]
                assert result == shot_id, f"Character related_shot_id 错误: {result}"
                print(f"✅ Character.related_shot_id = {result}")
                
                # 清理测试数据
                print("\n[8] 清理测试数据...")
                cur.execute("DELETE FROM character WHERE character_id = %s", (char_id,))
                cur.execute("DELETE FROM shot WHERE shot_id = %s", (shot_id,))
                cur.execute("DELETE FROM topic WHERE topic_id = %s", (topic_id,))
                conn.commit()
                print("✅ 测试数据已清理")
                
        print("\n" + "=" * 60)
        print("🎉 测试通过！两阶段处理逻辑正确")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_insert_with_null_fk()
    sys.exit(0 if success else 1)
