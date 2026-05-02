import os
import sys
import psycopg2
from dotenv import load_dotenv
import uuid

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.admissions.utils import sanitize_key

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

# Psycopg2 requires postgresql:// instead of postgresql+asyncpg://
if "postgresql+asyncpg://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

def ingest_departments():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    dept_dir = "data/departments"
    if not os.path.exists(dept_dir):
        print(f"Error: Directory {dept_dir} not found.")
        return

    print(f"Starting ingestion from {dept_dir}...")

    for filename in os.listdir(dept_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(dept_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # We'll use the sanitized key as the name or store the original name
                # Let's store the original name as 'name' and the content as 'description'
                dept_name = os.path.splitext(filename)[0]
                
                # Using an UPSERT (ON CONFLICT) to update description if name exists
                cur.execute("""
                    INSERT INTO departments (id, name, description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (name) DO UPDATE 
                    SET description = EXCLUDED.description;
                """, (str(uuid.uuid4()), dept_name, content))
                
                print(f"Ingested: {dept_name}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("Ingestion complete!")

if __name__ == "__main__":
    ingest_departments()
