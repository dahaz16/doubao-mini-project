# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 users 表添加 user_name 和 redeem_code 字段
执行日期：2026-02-01
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def add_user_fields():
    """为 users 表添加 user_name 和 redeem_code 字段"""
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            
            logging.info("=" * 60)
            logging.info("开始为 users 表添加新字段...")
            logging.info("=" * 60)
            
            # 1. 检查字段是否已存在
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name IN ('user_name', 'redeem_code')
            """)
            existing_fields = [row[0] for row in cursor.fetchall()]
            
            if 'user_name' in existing_fields and 'redeem_code' in existing_fields:
                logging.warning("⚠️  字段 user_name 和 redeem_code 已存在，跳过添加")
                return
            
            # 2. 添加 user_name 字段（先设为可空，填充默认值后再改为 NOT NULL）
            if 'user_name' not in existing_fields:
                logging.info("📝 添加 user_name 字段...")
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN user_name VARCHAR(64)
                """)
                logging.info("  ✓ user_name 字段添加成功（暂时可空）")
                
                # 3. 为已存在的用户填充默认值
                logging.info("📝 为已存在用户填充 user_name 默认值...")
                cursor.execute("""
                    UPDATE users 
                    SET user_name = 'User_' || SUBSTRING(user_id::text FROM 1 FOR 8)
                    WHERE user_name IS NULL
                """)
                affected_rows = cursor.rowcount
                logging.info(f"  ✓ 已为 {affected_rows} 个用户填充默认值")
                
                # 4. 将 user_name 改为 NOT NULL
                logging.info("📝 设置 user_name 为 NOT NULL...")
                cursor.execute("""
                    ALTER TABLE users 
                    ALTER COLUMN user_name SET NOT NULL
                """)
                logging.info("  ✓ user_name 约束设置成功")
            else:
                logging.info("⏭️  user_name 字段已存在，跳过")
            
            # 5. 添加 redeem_code 字段
            if 'redeem_code' not in existing_fields:
                logging.info("📝 添加 redeem_code 字段...")
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN redeem_code CHAR(4)
                """)
                logging.info("  ✓ redeem_code 字段添加成功")
            else:
                logging.info("⏭️  redeem_code 字段已存在，跳过")
            
            # 提交事务
            conn.commit()
            logging.info("=" * 60)
            logging.info("✅ 字段添加完成！")
            logging.info("=" * 60)


def verify_fields():
    """验证字段添加是否成功"""
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            
            logging.info("\n" + "=" * 60)
            logging.info("验证字段结构...")
            logging.info("=" * 60)
            
            # 查询字段信息
            cursor.execute("""
                SELECT 
                    column_name, 
                    data_type, 
                    character_maximum_length,
                    is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users' 
                  AND column_name IN ('user_name', 'redeem_code')
                ORDER BY column_name
            """)
            
            fields = cursor.fetchall()
            
            if len(fields) == 0:
                logging.error("❌ 未找到新添加的字段！")
                return False
            
            print("\n字段信息：")
            print("-" * 60)
            for field in fields:
                col_name, data_type, max_length, nullable = field
                print(f"字段名: {col_name}")
                print(f"  数据类型: {data_type}")
                print(f"  最大长度: {max_length}")
                print(f"  可为空: {nullable}")
                print("-" * 60)
            
            # 验证约束
            success = True
            
            # 检查 user_name
            user_name_field = next((f for f in fields if f[0] == 'user_name'), None)
            if user_name_field:
                if user_name_field[1] == 'character varying' and user_name_field[2] == 64 and user_name_field[3] == 'NO':
                    logging.info("✅ user_name 字段验证通过")
                else:
                    logging.error(f"❌ user_name 字段配置不正确: {user_name_field}")
                    success = False
            else:
                logging.error("❌ user_name 字段不存在")
                success = False
            
            # 检查 redeem_code
            redeem_code_field = next((f for f in fields if f[0] == 'redeem_code'), None)
            if redeem_code_field:
                if redeem_code_field[1] == 'character' and redeem_code_field[2] == 4:
                    logging.info("✅ redeem_code 字段验证通过")
                else:
                    logging.error(f"❌ redeem_code 字段配置不正确: {redeem_code_field}")
                    success = False
            else:
                logging.error("❌ redeem_code 字段不存在")
                success = False
            
            # 查询示例数据
            cursor.execute("""
                SELECT user_id, user_name, redeem_code, wechat_nickname
                FROM users
                LIMIT 5
            """)
            
            sample_data = cursor.fetchall()
            if sample_data:
                print("\n示例数据：")
                print("-" * 60)
                for row in sample_data:
                    print(f"User ID: {row[0]}")
                    print(f"  user_name: {row[1]}")
                    print(f"  redeem_code: {row[2]}")
                    print(f"  wechat_nickname: {row[3]}")
                    print("-" * 60)
            
            logging.info("=" * 60)
            
            return success


if __name__ == "__main__":
    try:
        # 1. 添加字段
        add_user_fields()
        
        # 2. 验证字段
        verify_success = verify_fields()
        
        if verify_success:
            print("\n🎉 数据库迁移成功完成！")
        else:
            print("\n⚠️  迁移完成但验证发现问题，请检查上方日志")
            
    except Exception as e:
        logging.error(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
