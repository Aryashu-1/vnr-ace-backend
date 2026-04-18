import os
import json
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DB URL and format it for psycopg2
db_url = os.getenv("DATABASE_URL")
if db_url and "postgresql+asyncpg://" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

IMPORT_DIR = 'data/import'

# The exact order matters for foreign key constraints!
TABLES_ORDER = [
    'departments',
    'companies',
    'profiles',
    'students',
    'faculty',
    'faculty_timetable',
    'placement_drives',
    'placement_applications',
    'placement_offers',
    'interview_experiences',
    'interview_rounds',
    'interview_questions'
]

def get_connection():
    return psycopg2.connect(db_url)

def upload_data():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        print("Connected to the database successfully.\n")

        for table in TABLES_ORDER:
            file_path = os.path.join(IMPORT_DIR, f"{table}.json")
            if not os.path.exists(file_path):
                print(f"Warning: File not found -> {file_path}. Skipping.")
                continue
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if not data:
                print(f"[{table}] No data to upload. Skipping.")
                continue

            # Extract column names from the first record
            columns = list(data[0].keys())
            
            # Prepare values as a list of tuples
            values = [[row.get(col) for col in columns] for row in data]
            
            # Create the INSERT statement dynamically
            columns_str = ", ".join(columns)
            
            # For ON CONFLICT DO NOTHING, we need to handle potential PK conflicts
            # This is generic so we just ON CONFLICT DO NOTHING (assumes 'id' is PK or unique constraint exists)
            # Some tables like placement_applications have unique constraints instead of standard single PKs
            # Standard DO NOTHING is safe to avoid crashing on re-runs
            insert_query = f"""
                INSERT INTO {table} ({columns_str})
                VALUES %s
                ON CONFLICT DO NOTHING
            """
            
            try:
                # Use execute_values for efficient batch insertion
                execute_values(cur, insert_query, values)
                print(f"[{table}] Successfully processed {len(data)} records.")
            except Exception as e:
                print(f"[{table}] Error uploading data: {e}")
                # We could rollback and continue, but usually, if one fails, subsequent ones might fail due to FK constraints
                conn.rollback()
                print("Aborting remaining uploads due to error.")
                return

        # Commit all the successful insertions
        conn.commit()
        print("\nAll data uploaded successfully!")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Database connection or fatal error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    upload_data()
