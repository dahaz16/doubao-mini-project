
import logging
from backend.database import get_db_connection
from backend.admin_service import delete_user_interview_records

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_user_data():
    """
    执行数据修正操作：
    1. 删除 user_id: fd2ca273-de6b-4cc6-bb1f-ca799e81890b 及其所有关联数据
    2. 重命名 user_id: f5577e07-00b5-4394-836b-cd145a453a69 的 user_name 为 "啊拓啊拓"
    """
    
    # 待操作的用户 ID
    DELETE_USER_ID = "fd2ca273-de6b-4cc6-bb1f-ca799e81890b"
    RENAME_USER_ID = "f5577e07-00b5-4394-836b-cd145a453a69"
    NEW_USER_NAME = "啊拓啊拓"

    print("\n🚀 开始执行数据修正任务...\n")

    try:
        # ------------ 操作 1: 删除用户及其关联数据 ------------
        print(f"1️⃣  正在删除用户 {DELETE_USER_ID} 的所有关联记录...")
        
        # 1.1 先调用 admin_service 中的函数删除所有外键关联的采访记录
        try:
            # 注意：delete_user_interview_records 是 async 函数，但在脚本中我们可以尝试直接复用其逻辑，
            # 或者因为它是被设计为 API 处理函数，这里我们手动执行 SQL 更稳妥且不需要 asyncio 环境
            # 为了简单起见，我直接重写 SQL 逻辑，确保同步执行
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 复用 admin_service.py 中的删除逻辑
                    
                    # 1. llm_processed
                    cursor.execute("DELETE FROM llm_processed WHERE user_id = %s", (DELETE_USER_ID,))
                    c1 = cursor.rowcount
                    
                    # 2. asr_processed
                    cursor.execute("""
                        DELETE FROM asr_processed 
                        WHERE original_text_id IN (
                            SELECT interview_original_text_id FROM interview_original_text WHERE user_id = %s
                        )
                    """, (DELETE_USER_ID,))
                    c2 = cursor.rowcount
                    
                    # 3. tts_processed
                    cursor.execute("""
                        DELETE FROM tts_processed 
                        WHERE link_original_text_id IN (
                            SELECT interview_original_text_id FROM interview_original_text WHERE user_id = %s
                        )
                    """, (DELETE_USER_ID,))
                    c3 = cursor.rowcount
                    
                    # 4. interview_original_voice
                    cursor.execute("DELETE FROM interview_original_voice WHERE user_id = %s", (DELETE_USER_ID,))
                    c4 = cursor.rowcount
                    
                    # 5. interview_original_text (必须在 llm_processed 删除后)
                    cursor.execute("DELETE FROM interview_original_text WHERE user_id = %s", (DELETE_USER_ID,))
                    c5 = cursor.rowcount
                    
                    # 6. character
                    cursor.execute("DELETE FROM character WHERE user_id = %s", (DELETE_USER_ID,))
                    c6 = cursor.rowcount
                    
                    # 7. shot
                    cursor.execute("DELETE FROM shot WHERE user_id = %s", (DELETE_USER_ID,))
                    c7 = cursor.rowcount
                    
                    # 8. topic
                    cursor.execute("DELETE FROM topic WHERE user_id = %s", (DELETE_USER_ID,))
                    c8 = cursor.rowcount
                    
                    # 9. stage
                    cursor.execute("DELETE FROM stage WHERE user_id = %s", (DELETE_USER_ID,))
                    c9 = cursor.rowcount
                    
                    # 10. hintboard
                    cursor.execute("DELETE FROM hintboard WHERE user_id = %s", (DELETE_USER_ID,))
                    c10 = cursor.rowcount
                    
                    # 11. storyboard
                    cursor.execute("DELETE FROM storyboard WHERE user_id = %s", (DELETE_USER_ID,))
                    c11 = cursor.rowcount
                    
                    # 12. narration_status
                    cursor.execute("DELETE FROM narration_status WHERE user_id = %s", (DELETE_USER_ID,))
                    c12 = cursor.rowcount
                    
                    # 13. 最后删除 users 表本身
                    cursor.execute("DELETE FROM users WHERE user_id = %s", (DELETE_USER_ID,))
                    c_user = cursor.rowcount
                    
                    conn.commit()
                    
                    print(f"   - 采访记录删除统计: 文本:{c5}, 语音:{c4}, LLM记录:{c1}, Topic:{c8}, Stage:{c9}")
                    if c_user > 0:
                        print(f"   ✅ 用户 {DELETE_USER_ID} 已从 users 表中彻底删除。")
                    else:
                        print(f"   ⚠️  未在 users 表中找到 ID 为 {DELETE_USER_ID} 的用户 (可能已被删除)。")

        except Exception as e:
            print(f"   ❌ 删除用户操作失败: {e}")
            raise e

        # ------------ 操作 2: 重命名用户 ------------
        print(f"\n2️⃣  正在更新用户 {RENAME_USER_ID} 的昵称...")
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET user_name = %s WHERE user_id = %s", 
                        (NEW_USER_NAME, RENAME_USER_ID)
                    )
                    if cursor.rowcount > 0:
                        print(f"   ✅ 用户名已成功更新为: {NEW_USER_NAME}")
                        conn.commit()
                    else:
                        print(f"   ⚠️  未找到 ID 为 {RENAME_USER_ID} 的用户，更新未生效。")
                        
        except Exception as e:
            print(f"   ❌ 更新用户名失败: {e}")
            raise e

    except Exception as e:
        print(f"\n❌ 脚本执行出错: {e}")

if __name__ == "__main__":
    fix_user_data()
