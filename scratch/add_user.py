import os
import psycopg2
from dotenv import load_dotenv
import uuid
from core.auth_utils import hash_password

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url and "postgresql+asyncpg://" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

def create_user():
    email = "22071a05b4@vnrvjiet.in"
    password = "student123"
    full_name = "Aryashu"
    roll_no = "22071A05B4"
    branch_name = "CSE"
    
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # 1. Get or Create Department
        cur.execute("SELECT id FROM departments WHERE name ILIKE %s", (f"%{branch_name}%",))
        dept_row = cur.fetchone()
        if dept_row:
            dept_id = dept_row[0]
        else:
            dept_id = str(uuid.uuid4())
            cur.execute("INSERT INTO departments (id, name) VALUES (%s, %s)", (dept_id, branch_name))
            print(f"Created department: {branch_name}")

        # 2. Create Profile
        profile_id = str(uuid.uuid4())
        hashed_pw = hash_password(password)
        
        cur.execute("""
            INSERT INTO profiles (id, full_name, email, user_type, hashed_password, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name RETURNING id;
        """, (profile_id, full_name, email, 'student', hashed_pw, 'active'))
        
        result = cur.fetchone()
        if result:
            profile_id = result[0]
            print(f"Profile created/updated for {email}")
        
        # 3. Create Student
        cur.execute("""
            INSERT INTO students (roll_no, profile_id, department_id, section, current_year, cgpa, placement_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (roll_no) DO NOTHING;
        """, (roll_no, profile_id, dept_id, 'B', 2, 9.2, 'unplaced'))
        
        conn.commit()
        print(f"Successfully added student {roll_no} into DB.")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    create_user()
