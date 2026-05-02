import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_test_data():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    # Get 3 faculty names and their subjects
    cur.execute("""
        SELECT p.full_name, f.id, t.faculty_id, t.subject 
        FROM profiles p 
        JOIN faculty f ON f.profile_id = p.id 
        JOIN faculty_timetable t ON t.faculty_id = f.id 
        LIMIT 5
    """)
    rows = cur.fetchall()
    
    print("--- LINKAGE CHECK ---")
    for row in rows:
        print(f"Faculty: {row[0]} | FID: {row[1]} | TFID: {row[2]} | Sub: {row[3]}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    get_test_data()
