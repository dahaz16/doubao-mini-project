from backend.database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)

def enable_llm_caching():
    key = 'enable_llm_caching'
    value = 'true'
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info(f"Updating {key} to {value}...")
            cursor.execute("""
                INSERT INTO sys_config (config_key, config_name, config_value, config_type, remark)
                VALUES (%s, '启用 LLM 缓存', %s, 'select', '全局控制 Intv/Stn/Dir 的 Session Caching')
                ON CONFLICT (config_key) DO UPDATE SET
                    config_value = EXCLUDED.config_value,
                    updated_time = CURRENT_TIMESTAMP
            """, (key, value))
            conn.commit()
            logging.info("Done.")

if __name__ == "__main__":
    enable_llm_caching()
