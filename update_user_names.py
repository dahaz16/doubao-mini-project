
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.pool import SimpleConnectionPool

# Ensure we can import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def update_user_names():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Update User 1
        user1_id = "f5577e07-00b5-4394-836b-cd145a453a69"
        user1_name = "啊拓"
        cursor.execute("UPDATE users SET user_name = %s WHERE user_id = %s", (user1_name, user1_id))
        print(f"Updated user {user1_id} name to {user1_name}")

        # Update User 2
        user2_id = "32826937-85e6-46cb-812b-e5632fffa5a6"
        user2_name = "慕云"
        cursor.execute("UPDATE users SET user_name = %s WHERE user_id = %s", (user2_name, user2_id))
        print(f"Updated user {user2_id} name to {user2_name}")

        conn.commit()
        cursor.close()
        conn.close()
        print("Database update successful.")

    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    update_user_names()
