import os
import json
import pandas as pd
import psycopg2
from uuid import uuid4
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    url = DATABASE_URL
    if 'postgresql+asyncpg://' in url:
        url = url.replace('postgresql+asyncpg://', 'postgresql://')
    return psycopg2.connect(url)

def migrate():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        print("Connected to Supabase.")

        # 1. Load Data
        print("Loading data files...")
        with open('data/faculty_data.json', 'r') as f:
            faculty_data = json.load(f)
        with open('data/students_sample.json', 'r') as f:
            students_sample = json.load(f)
        with open('data/classwork_students.json', 'r') as f:
            classwork_students = json.load(f)
        with open('data/companies_sample.json', 'r') as f:
            companies_sample = json.load(f)
        with open('data/placements_sample.json', 'r') as f:
            placements_sample = json.load(f)
        with open('data/placements/interview_experiences.json', 'r') as f:
            interview_exp_data = json.load(f)
        
        student_xlsx = pd.read_excel('data/student_data.xlsx')
        print(f"XLSX Columns: {student_xlsx.columns.tolist()}")
        print("Data loaded successfully.")

        # Mapping dictionaries
        dept_map = {} # name -> uuid
        profile_map = {} # email -> uuid
        student_map = {} # roll_no -> uuid
        faculty_map = {} # name -> uuid
        company_map = {} # name -> uuid
        drive_map = {} # comp_id -> uuid (simplified)

        # 2. Departments
        print("Migrating Departments...")
        depts = set()
        for f in faculty_data: depts.add(f.get('department'))
        for s in students_sample: depts.add(s.get('branch'))
        for s in classwork_students: depts.add(s.get('branch'))
        for _, row in student_xlsx.iterrows(): 
            d = row.get('branch') or row.get('Course') or row.get('department')
            if d: depts.add(d)
        
        for dept_name in depts:
            if not dept_name or pd.isna(dept_name): continue
            dept_id = str(uuid4())
            cur.execute("INSERT INTO departments (id, name) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id", (dept_id, dept_name))
            actual_id = cur.fetchone()[0]
            dept_map[dept_name] = actual_id

        # 3. Companies
        print("Migrating Companies...")
        for c in companies_sample:
            company_id = str(uuid4())
            cur.execute("INSERT INTO companies (id, name, sector) VALUES (%s, %s, %s) ON CONFLICT (name) DO UPDATE SET sector = EXCLUDED.sector RETURNING id", 
                        (company_id, c['name'], c.get('sector')))
            actual_id = cur.fetchone()[0]
            company_map[c['name']] = actual_id

        # 4. Students and Profiles
        print("Migrating Students and Profiles (Merging Data)...")
        combined_students = {}
        
        # Merge order: JSON Sample -> Classwork JSON -> XLSX
        for s in students_sample:
            roll = s['roll_no']
            combined_students[roll] = {
                'roll_no': roll,
                'name': s.get('full_name'),
                'branch': s.get('branch'),
                'cgpa': s.get('cgpa'),
                'gender': s.get('gender'),
                'minor_degree': s.get('minor_degree')
            }
        
        for s in classwork_students:
            roll = s['roll_no']
            if roll not in combined_students:
                combined_students[roll] = {'roll_no': roll}
            combined_students[roll].update({
                'name': s.get('name') or combined_students[roll].get('name'),
                'branch': s.get('branch') or combined_students[roll].get('branch'),
                'section': s.get('section'),
                'cgpa': s.get('cgpa') or combined_students[roll].get('cgpa'),
                'email': s.get('email'),
                'backlogs': s.get('backlogs')
            })

        for _, row in student_xlsx.iterrows():
            roll = str(row.get('roll_number') or row.get('Roll No') or row.get('roll_no'))
            if not roll or roll == 'nan': continue
            if roll not in combined_students:
                combined_students[roll] = {'roll_no': roll}
            
            combined_students[roll].update({
                'name': row.get('name') or row.get('Name') or combined_students[roll].get('name'),
                'branch': row.get('branch') or row.get('Course') or combined_students[roll].get('branch'),
                'section': row.get('section') or combined_students[roll].get('section'),
                'cgpa': row.get('cumulative_gpa') or row.get('CGPA') or combined_students[roll].get('cgpa'),
                'attendance': row.get('attendance_pct'),
                'backlogs': row.get('backlogs') or combined_students[roll].get('backlogs')
            })

        for roll, s_data in combined_students.items():
            email = s_data.get('email') or f"{roll.lower()}@vnr.edu.in"
            name = s_data.get('name') or 'Student'
            
            # Profile
            cur.execute("INSERT INTO profiles (full_name, email, user_type) VALUES (%s, %s, %s) ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name RETURNING id",
                        (name, email, 'student'))
            profile_uuid = cur.fetchone()[0]
            
            # Student
            dept_id = dept_map.get(s_data.get('branch'))
            cur.execute("""
                INSERT INTO students (profile_id, roll_no, department_id, section, cgpa, backlogs, gender, minor_degree) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                ON CONFLICT (roll_no) DO UPDATE SET cgpa = EXCLUDED.cgpa 
                RETURNING id
            """, (profile_uuid, roll, dept_id, s_data.get('section'), s_data.get('cgpa'), s_data.get('backlogs', 0), s_data.get('gender'), s_data.get('minor_degree')))
            student_uuid = cur.fetchone()[0]
            student_map[roll] = student_uuid

        # 5. Faculty
        print("Migrating Faculty...")
        for f in faculty_data:
            email = f.get('email') or f"{f['name'].lower().replace(' ', '.')}@faculty.vnr.edu.in"
            
            cur.execute("INSERT INTO profiles (full_name, email, user_type) VALUES (%s, %s, %s) ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name RETURNING id",
                        (f['name'], email, 'faculty'))
            profile_uuid = cur.fetchone()[0]
            
            dept_id = dept_map.get(f['department'])
            cur.execute("INSERT INTO faculty (profile_id, department_id, designation, cabin) VALUES (%s, %s, %s, %s) RETURNING id",
                        (profile_uuid, dept_id, f['designation'], f['cabin']))
            faculty_uuid = cur.fetchone()[0]
            
            # Timetable
            for day, sessions in f.get('schedule', {}).items():
                for session in sessions:
                    time_range = session.split('(')[0].strip() if '(' in session else session
                    subj = session.split('(')[1].replace(')', '').strip() if '(' in session else "General"
                    cur.execute("INSERT INTO faculty_timetable (faculty_id, day, time_range, subject) VALUES (%s, %s, %s, %s)",
                                (faculty_uuid, day, time_range, subj))

        # 6. Placement Drives
        print("Migrating Placement Drives...")
        for p in placements_sample:
            # Match company
            comp_id = None
            # Find company ID by numeric company_id in mapping (simplified)
            # Actually placements_sample has numeric student_id and company_id which refer to the sample json files
            c_name = next((c['name'] for c in companies_sample if c['id'] == p['company_id']), None)
            comp_id = company_map.get(c_name)
            
            if not comp_id: continue
            
            # Student roll
            s_roll = next((s['roll_no'] for s in students_sample if s['id'] == p['student_id']), None)
            s_uuid = student_map.get(s_roll)
            
            if not s_uuid: continue
            
            # Create Drive
            drive_date = p['placement_date'][:10]
            cur.execute("INSERT INTO placement_drives (company_id, drive_date, ctc, status) VALUES (%s, %s, %s, %s) RETURNING id",
                        (comp_id, drive_date, p['ctc_lpa'], 'completed'))
            drive_uuid = cur.fetchone()[0]
            
            # App and Offer
            cur.execute("INSERT INTO placement_applications (student_id, drive_id, status) VALUES (%s, %s, %s)",
                        (s_uuid, drive_uuid, 'selected'))
            cur.execute("INSERT INTO placement_offers (student_id, drive_id, offered_ctc, accepted) VALUES (%s, %s, %s, %s)",
                        (s_uuid, drive_uuid, p['ctc_lpa'], True))

        # 7. Interview Experiences
        print("Migrating Interview Experiences...")
        for corp in interview_exp_data['companies']:
            comp_name = corp['name']
            comp_id = company_map.get(comp_name)
            if not comp_id:
                cur.execute("INSERT INTO companies (name) VALUES (%s) RETURNING id", (comp_name,))
                comp_id = cur.fetchone()[0]
                company_map[comp_name] = comp_id
            
            for exp in corp['experiences']:
                cur.execute("INSERT INTO interview_experiences (company_id, overall_experience) VALUES (%s, %s) RETURNING id",
                            (comp_id, f"Experience of {exp['candidate']}"))
                exp_uuid = cur.fetchone()[0]
                
                for idx, r in enumerate(exp['rounds']):
                    cur.execute("INSERT INTO interview_rounds (experience_id, round_type, round_order) VALUES (%s, %s, %s) RETURNING id",
                                (exp_uuid, r['round'], idx + 1))
                    round_uuid = cur.fetchone()[0]
                    
                    for q in r['questions']:
                        cur.execute("INSERT INTO interview_questions (round_id, question_text, topic) VALUES (%s, %s, %s)",
                                    (round_uuid, q['question'], ", ".join(q.get('tags', []))))

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        if conn: conn.rollback()
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    migrate()
