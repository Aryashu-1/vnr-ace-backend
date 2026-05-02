import os
import json
import uuid
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==============================
# 🔌 DB CONNECTION
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

# Psycopg2 requires postgresql:// instead of postgresql+asyncpg://
if "postgresql+asyncpg://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ==============================
# 🧠 HELPERS
# ==============================

# Mapping for branches to department names in the DB
DEPT_MAPPING = {
    "CE": "CIVIL",
    "CSE": "CSE",
    "IT": "IT",
    "ECE": "ECE",
    "EEE": "EEE",
    "ME": "MECH",
    "H&S": "H&S",
    "CSBS": "CSE"
}

def get_dept_id(branch_code):
    dept_name = DEPT_MAPPING.get(branch_code, branch_code)
    cur.execute("SELECT id FROM departments WHERE name = %s", (dept_name,))
    res = cur.fetchone()
    if res:
        return res[0]
    
    # Create if not exists
    did = str(uuid.uuid4())
    cur.execute("INSERT INTO departments (id, name) VALUES (%s, %s)", (did, dept_name))
    return did

def get_or_create_faculty(name, branch_code):
    # 1. Search Profile
    cur.execute("SELECT id FROM profiles WHERE full_name = %s", (name,))
    res = cur.fetchone()
    
    if res:
        profile_id = res[0]
        # Check if faculty entry exists
        cur.execute("SELECT id FROM faculty WHERE profile_id = %s", (profile_id,))
        fac_res = cur.fetchone()
        if fac_res:
            return fac_res[0]
    else:
        # Create Profile
        profile_id = str(uuid.uuid4())
        email = f"{name.lower().replace(' ', '.')}@vnr.edu.in"
        cur.execute(
            "INSERT INTO profiles (id, full_name, email, user_type) VALUES (%s, %s, %s, %s)",
            (profile_id, name, email, 'faculty')
        )
    
    # Create Faculty
    fac_id = str(uuid.uuid4())
    dept_id = get_dept_id(branch_code)
    cur.execute(
        "INSERT INTO faculty (id, profile_id, department_id) VALUES (%s, %s, %s)",
        (fac_id, profile_id, dept_id)
    )
    return fac_id

def slot_to_time(slot_num):
    mapping = {
        1: "09:00-10:00",
        2: "10:00-11:00",
        3: "11:00-12:00",
        4: "12:00-13:00",
        5: "14:00-15:00",
        6: "15:00-16:00",
        7: "16:00-17:00"
    }
    return mapping.get(slot_num, "09:00-10:00")

# ==============================
# 📥 MAIN INGEST FUNCTION
# ==============================

def ingest_file(file_path):
    print(f"Processing: {file_path}")

    with open(file_path, "r") as f:
        data = json.load(f)

    meta = data["metadata"]
    branch = meta["branch"]
    section = meta["section"]
    year = meta["year"]
    room = meta.get("room_no", "")
    
    class_label = f"{branch}-{section}"

    subject_info = data["subjects"]

    # 🔹 Insert timetable slots into faculty_timetable
    for day_data in data["schedule"]:
        day = day_data["day"]

        for slot in day_data["slots"]:
            slot_num = slot["slot"]
            subject_key = slot.get("subject")
            time_range = slot_to_time(slot_num)

            if subject_key is None:
                continue

            # 🔁 Handle lab arrays or single subjects
            keys = subject_key if isinstance(subject_key, list) else [subject_key]
            
            for k in keys:
                details = subject_info.get(k)
                if not details:
                    continue
                
                subj_name = details.get("name", k)
                faculty_names = details.get("faculty", [])
                
                activity = f"{subj_name} ({class_label})"
                
                for fac_name in faculty_names:
                    fac_id = get_or_create_faculty(fac_name, branch)
                    
                    cur.execute(
                        """
                        INSERT INTO faculty_timetable (id, faculty_id, day, time_range, subject, room)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (str(uuid.uuid4()), fac_id, day, time_range, activity, room)
                    )

    conn.commit()
    print(f"Ingested: {file_path}")


# ==============================
# 🔁 BULK INGEST
# ==============================

def ingest_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"Error: Folder {folder_path} not found.")
        return

    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            try:
                ingest_file(os.path.join(folder_path, file))
            except Exception as e:
                conn.rollback()
                print(f"Error in {file}: {e}")


# ==============================
# 🚀 RUN
# ==============================

if __name__ == "__main__":
    folder = "timetables_json" 
    ingest_folder(folder)

    cur.close()
    conn.close()
    print("All timetables ingested successfully!")