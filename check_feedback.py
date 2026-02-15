import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from backend.database import get_db_connection
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 查询所有反馈记录
            cursor.execute("""
                SELECT 
                    feedback_id,
                    user_id,
                    feedback_content,
                    feedback_voice_url,
                    created_time
                FROM feedback
                ORDER BY created_time DESC
                LIMIT 10;
            """)
            
            feedbacks = cursor.fetchall()
            
            if not feedbacks:
                print("❌ 数据库中没有反馈记录")
            else:
                print(f"✅ 找到 {len(feedbacks)} 条反馈记录:\n")
                for fb in feedbacks:
                    print(f"反馈ID: {fb[0]}")
                    print(f"用户ID: {fb[1]}")
                    print(f"反馈内容: {fb[2]}")
                    print(f"语音URL: {fb[3]}")
                    print(f"创建时间: {fb[4]}")
                    print("-" * 60)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
