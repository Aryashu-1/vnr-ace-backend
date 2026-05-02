import os
import psycopg2
from dotenv import load_dotenv
from core.auth_utils import hash_password

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url and "postgresql+asyncpg://" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

def seed_missing_passwords():
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        print("Connected to DB.")

        # Get all profiles with null passwords
        cur.execute("SELECT id, email, user_type FROM profiles WHERE hashed_password IS NULL")
        profiles = cur.fetchall()
        
        if not profiles:
            print("No profiles found with missing passwords.")
            return

        print(f"Found {len(profiles)} profiles with missing passwords.")

        for profile_id, email, user_type in profiles:
            # Default password based on role: {role}123
            # If role is unknown, default to user123
            role = user_type.lower() if user_type else "user"
            default_password = f"{role}123"
            hashed_pw = hash_password(default_password)
            
            cur.execute(
                "UPDATE profiles SET hashed_password = %s WHERE id = %s",
                (hashed_pw, profile_id)
            )
            print(f"Updated password for {email or 'unknown'} ({role}) -> {default_password}")

        conn.commit()
        print("Successfully seeded all missing passwords.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    seed_missing_passwords()
