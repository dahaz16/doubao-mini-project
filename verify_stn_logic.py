
import json
import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock
import uuid

# 将 backend 目录添加到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock 所有可能导致导入失败的模块
sys.modules['volcenginesdkarkruntime'] = MagicMock()
sys.modules['ai_service'] = MagicMock()
mock_ai = MagicMock()
mock_ai.get_doubao_chat_reply.return_value = "[]"
sys.modules['ai_service'] = mock_ai

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 现在可以尝试导入
try:
    import stn_service
    from stn_service import process_parsed_data
    from database import get_db_connection
    print("✅ 模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

async def verify_stn_logic():
    # 使用数据库中存在的真实 UserID 以及随机的 SessionID
    user_id = "ed23d507-59f0-4ac7-bdbf-ed8fd62784d9" 
    session_id = str(uuid.uuid4())
    
    print(f"Using UserID: {user_id}")
    print(f"Using SessionID: {session_id}")

    # 1. 加载样例数据
    md_file_path = "/Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project/PRD docs/测试材料：Stn输出JSON 样例-采访 3:4:5.md"
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 找到 JSON 列表
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx == -1 or end_idx == 0:
                print("❌ 未在文档中找到 JSON 数据")
                return
            data_list = json.loads(content[start_idx:end_idx])
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return

    print("🚀 开始执行 Stn 逻辑验证...")
    
    # 2. 调用处理函数
    try:
        await process_parsed_data(user_id, session_id, data_list)
        print("✅ process_parsed_data 执行完成")
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. 验证数据库结果
    print("\n--- 数据库验证开始 ---")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 检查 Stages
                cursor.execute("SELECT stage_id, stage_title, stage_summary FROM stage WHERE user_id = %s AND session_id = %s", (user_id, session_id))
                stages = cursor.fetchall()
                print(f"\n[Stage 表] 数量: {len(stages)}")
                for s in stages:
                    print(f"  ID: {s[0]}, Title: {s[1]}, Summary: {s[2][:30] if s[2] else ''}...")

                # 检查 Topics
                cursor.execute("SELECT topic_id, parent_stage_id, topic_title FROM topic WHERE user_id = %s AND session_id = %s", (user_id, session_id))
                topics = cursor.fetchall()
                print(f"\n[Topic 表] 数量: {len(topics)}")
                for t in topics:
                    print(f"  ID: {t[0]}, StageID: {t[1]}, Title: {t[2]}")

                # 检查 Shots
                cursor.execute("SELECT shot_id, parent_topic_id, shot_title FROM shot WHERE user_id = %s AND session_id = %s", (user_id, session_id))
                shots = cursor.fetchall()
                print(f"\n[Shot 表] 数量: {len(shots)}")
                for sh in shots:
                    print(f"  ID: {sh[0]}, TopicID: {sh[1]}, Title: {sh[2]}")

                # 检查 Characters
                cursor.execute("SELECT character_id, related_shot_id, name, relation FROM character WHERE user_id = %s AND session_id = %s", (user_id, session_id))
                chars = cursor.fetchall()
                print(f"\n[Character 表] 数量: {len(chars)}")
                for c in chars:
                    print(f"  ID: {c[0]}, ShotID: {c[1]}, Name: {c[2]}, Relation: {c[3]}")

                # 检查 Story Board
                cursor.execute("SELECT story_id, story_type, story_content FROM story_board WHERE user_id = %s AND session_id = %s ORDER BY story_id ASC", (user_id, session_id))
                sb = cursor.fetchall()
                print(f"\n[Story Board 表] 数量: {len(sb)}")
                for row in sb:
                    print(f"  Type {row[1]}: {row[2]}")
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")

    print("\n--- 验证结束 ---")

if __name__ == "__main__":
    asyncio.run(verify_stn_logic())
