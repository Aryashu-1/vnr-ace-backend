import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'faculty_timetable'
""")

columns = cur.fetchall()
print("Columns in faculty_timetable:")
for col in columns:
    print(f"- {col[0]} ({col[1]})")

cur.close()
conn.close()
