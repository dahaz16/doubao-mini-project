# -*- coding: utf-8 -*-
"""
数据库操作模块 - PostgreSQL 版本
使用 psycopg2 连接 Supabase PostgreSQL 数据库
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import os
from dotenv import load_dotenv
from contextlib import contextmanager
import logging

# 加载环境变量
load_dotenv()

# 数据库连接字符串
DATABASE_URL = os.getenv("DATABASE_URL")

# 连接池（提高性能）
connection_pool = None

def init_connection_pool():
    """初始化数据库连接池"""
    global connection_pool
    if connection_pool is None:
        try:
            connection_pool = SimpleConnectionPool(
                minconn=2,
                maxconn=20,  # 🔧 增加最大连接数,支持更多并发请求
                dsn=DATABASE_URL,
                # 🔧 添加连接超时设置
                connect_timeout=10,  # 连接超时 10 秒
                options='-c statement_timeout=30000'  # SQL 语句超时 30 秒
            )
            logging.info("✅ 数据库连接池初始化成功 (minconn=2, maxconn=20)")
        except Exception as e:
            logging.error(f"❌ 数据库连接池初始化失败: {e}")
            raise

@contextmanager
def get_db_connection():
    """
    获取数据库连接的上下文管理器
    使用 with 语句自动管理连接的获取和释放
    
    🔧 v3.9 修复: 添加连接健康检查,防止使用僵尸连接
    - 每次使用前先测试连接是否健康
    - 如果连接失效,自动重新获取新连接
    - 最多重试 3 次
    """
    if connection_pool is None:
        init_connection_pool()
    
    conn = None
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # 从连接池获取连接
            conn = connection_pool.getconn()
            
            # 🔍 健康检查: 测试连接是否可用
            with conn.cursor() as test_cursor:
                test_cursor.execute("SELECT 1")
                test_cursor.fetchone()
            
            # 连接健康,可以使用
            if attempt > 0:
                logging.info(f"✅ 数据库连接健康检查通过 (重试 {attempt} 次后成功)")
            
            break  # 成功获取健康连接,跳出重试循环
            
        except Exception as e:
            # 连接不健康,记录日志
            logging.warning(f"⚠️ 数据库连接健康检查失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            
            # 关闭失效的连接
            if conn:
                try:
                    conn.close()
                except:
                    pass
                conn = None
            
            # 如果是最后一次尝试,抛出异常
            if attempt == max_retries - 1:
                logging.error(f"❌ 数据库连接获取失败,已重试 {max_retries} 次")
                raise
            
            # 否则继续重试
            continue
    
    try:
        yield conn
    finally:
        # 归还连接到连接池
        if conn:
            connection_pool.putconn(conn)

def close_connection_pool():
    """关闭数据库连接池"""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        logging.info("数据库连接池已关闭")

def init_db():
    """
    初始化数据库表结构（如果不存在）
    目前保留原有的 records 表，后续会创建完整的 16 张表
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    user_input TEXT NOT NULL,
                    ai_summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logging.info("数据库表初始化成功")

def insert_record(user_input: str, ai_summary: str) -> int:
    """
    插入新的交互记录到数据库
    
    Args:
        user_input: 用户输入内容
        ai_summary: AI 摘要内容
    
    Returns:
        int: 新插入记录的 ID
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO records (user_input, ai_summary)
                VALUES (%s, %s)
                RETURNING id
            """, (user_input, ai_summary))
            record_id = cursor.fetchone()[0]
            conn.commit()
            return record_id

def get_records(limit: int = 10):
    """
    获取最新的记录
    
    Args:
        limit: 返回记录数量限制
    
    Returns:
        list: 记录列表（字典格式）
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM records 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

def test_connection():
    """
    测试数据库连接
    
    Returns:
        bool: 连接成功返回 True，失败返回 False
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                logging.info(f"数据库连接成功！PostgreSQL 版本: {version}")
                return True
    except Exception as e:
        logging.error(f"数据库连接失败: {e}")
        return False
