from backend.database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)

def disable_llm_caching():
    key = 'enable_llm_caching'
    new_value = 'false'
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check current value
                cursor.execute("SELECT config_value FROM sys_config WHERE config_key = %s", (key,))
                result = cursor.fetchone()
                current_value = result[0] if result else "NOT FOUND"
                logging.info(f"Current {key}: {current_value}")
                
                # Update value
                cursor.execute("""
                    UPDATE sys_config 
                    SET config_value = %s 
                    WHERE config_key = %s
                """, (new_value, key))
                
                if cursor.rowcount == 0:
                    # Insert if not exists (though it should exist based on previous check)
                    cursor.execute("""
                        INSERT INTO sys_config (config_key, config_value, config_type, description)
                        VALUES (%s, %s, 'text', 'Enable LLM Context Caching')
                    """, (key, new_value))
                    logging.info(f"Inserted {key} = {new_value}")
                else:
                    logging.info(f"Updated {key} to {new_value}")
                
                conn.commit()
                
                # Verify
                cursor.execute("SELECT config_value FROM sys_config WHERE config_key = %s", (key,))
                final_result = cursor.fetchone()
                logging.info(f"Final {key}: {final_result[0]}")

    except Exception as e:
        logging.error(f"Failed to update config: {e}")

if __name__ == "__main__":
    disable_llm_caching()
