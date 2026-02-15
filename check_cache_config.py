from backend.database import get_db_connection

def check_config():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT config_value FROM sys_config WHERE config_key = 'enable_caching'")
            result = cursor.fetchone()
            if result:
                print(f"Current enable_caching value: {result[0]}")
            else:
                print("enable_caching config key not found.")
            
            # Also check enable_llm_caching as seen in the code llm_api_service.py:133
            cursor.execute("SELECT config_value FROM sys_config WHERE config_key = 'enable_llm_caching'")
            result = cursor.fetchone()
            if result:
                print(f"Current enable_llm_caching value: {result[0]}")
            else:
                print("enable_llm_caching config key not found.")

if __name__ == "__main__":
    check_config()
