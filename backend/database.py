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
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL
            )
            logging.info("数据库连接池初始化成功")
        except Exception as e:
            logging.error(f"数据库连接池初始化失败: {e}")
            raise

@contextmanager
def get_db_connection():
    """
    获取数据库连接的上下文管理器
    使用 with 语句自动管理连接的获取和释放
    """
    if connection_pool is None:
        init_connection_pool()
    
    conn = connection_pool.getconn()
    try:
        yield conn
    finally:
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
