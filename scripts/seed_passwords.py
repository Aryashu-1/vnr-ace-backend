import os
import psycopg2
from dotenv import load_dotenv
from uuid import uuid4
from core.auth_utils import hash_password

# Load environment variables
load_dotenv()

# Get DB URL and format it for psycopg2
db_url = os.getenv("DATABASE_URL")
if db_url and "postgresql+asyncpg://" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

def get_connection():
    return psycopg2.connect(db_url)

def seed_passwords_and_admin():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        print("Connected to the database successfully.")

        print("Seeding passwords for existing users...")
        
        student_hash = hash_password("student123")
        faculty_hash = hash_password("feculty123")
        admin_hash = hash_password("admin123")

        # Overwrite all passwords to use argon2
        cur.execute("UPDATE profiles SET hashed_password = %s WHERE user_type = 'student';", (student_hash,))
        print(f"Updated {cur.rowcount} student profiles.")
        
        cur.execute("UPDATE profiles SET hashed_password = %s WHERE user_type = 'faculty';", (faculty_hash,))
        print(f"Updated {cur.rowcount} faculty profiles.")

        # 3. Add Admin user
        print("Adding admin user...")
        admin_email = 'admina@vnr.com'
        
        cur.execute("SELECT id FROM profiles WHERE email = %s", (admin_email,))
        existing_admin = cur.fetchone()
        
        admin_id = str(uuid4())
        if existing_admin:
            print("Admin user already exists, updating password...")
            cur.execute("UPDATE profiles SET hashed_password = %s, user_type = 'admin' WHERE email = %s", (admin_hash, admin_email))
            admin_id = existing_admin[0]
        else:
            cur.execute("""
                INSERT INTO profiles (id, full_name, email, user_type, hashed_password)
                VALUES (%s, %s, %s, %s, %s)
            """, (admin_id, 'System Administrator', admin_email, 'admin', admin_hash))
            print("Admin user created.")

        conn.commit()
        print("\nPasswords re-seeded successfully with argon2!")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    seed_passwords_and_admin()
