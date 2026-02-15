from backend.database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)

def verify_caching_config():
    key = 'enable_llm_caching'
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT config_value FROM sys_config WHERE config_key = %s", (key,))
            result = cursor.fetchone()
            
            if result:
                value = result[0]
                print(f"✅ Config '{key}' found. Value: '{value}'")
                if str(value).lower() == 'true':
                    print("✅ Caching is ENABLED.")
                else:
                    print(f"❌ Caching is NOT enabled (value is {value}).")
            else:
                print(f"❌ Config '{key}' NOT found in database.")

if __name__ == "__main__":
    verify_caching_config()
