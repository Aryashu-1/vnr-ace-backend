import os
import json
import pandas as pd
from uuid import uuid4

def generate_json():
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
    print("Data loaded successfully.")

    # Output directory
    output_dir = 'data/import'
    os.makedirs(output_dir, exist_ok=True)

    # State
    tables = {
        'departments': [],
        'profiles': [],
        'students': [],
        'faculty': [],
        'faculty_timetable': [],
        'companies': [],
        'placement_drives': [],
        'placement_applications': [],
        'placement_offers': [],
        'interview_experiences': [],
        'interview_rounds': [],
        'interview_questions': []
    }

    dept_map = {} # name -> id
    student_map = {} # roll_no -> id
    faculty_map = {} # name -> id
    company_map = {} # name -> id

    # 2. Departments
    print("Processing Departments...")
    depts = set()
    for f in faculty_data: depts.add(f.get('department'))
    for s in students_sample: depts.add(s.get('branch'))
    for s in classwork_students: depts.add(s.get('branch'))
    for _, row in student_xlsx.iterrows(): 
        d = row.get('branch') or row.get('Course') or row.get('department')
        if d: depts.add(d)
    
    for dept_name in depts:
        if not dept_name or pd.isna(dept_name): continue
        d_id = str(uuid4())
        tables['departments'].append({'id': d_id, 'name': dept_name})
        dept_map[dept_name] = d_id

    # 3. Companies
    print("Processing Companies...")
    for c in companies_sample:
        c_id = str(uuid4())
        tables['companies'].append({'id': c_id, 'name': c['name'], 'sector': c.get('sector')})
        company_map[c['name']] = c_id

    # 4. Students and Profiles
    print("Processing Students and Profiles...")
    combined_students = {}
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
        if roll not in combined_students: combined_students[roll] = {'roll_no': roll}
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
        if roll not in combined_students: combined_students[roll] = {'roll_no': roll}
        combined_students[roll].update({
            'name': row.get('name') or row.get('Name') or combined_students[roll].get('name'),
            'branch': row.get('branch') or row.get('Course') or combined_students[roll].get('branch'),
            'section': row.get('section') or combined_students[roll].get('section'),
            'cgpa': row.get('cumulative_gpa') or row.get('CGPA') or combined_students[roll].get('cgpa'),
            'backlogs': row.get('backlogs') or combined_students[roll].get('backlogs')
        })

    for roll, s_data in combined_students.items():
        p_id = str(uuid4())
        email = s_data.get('email') or f"{roll.lower()}@vnr.edu.in"
        tables['profiles'].append({
            'id': p_id,
            'full_name': s_data.get('name') or 'Student',
            'email': email,
            'user_type': 'student'
        })
        
        s_id = str(uuid4())
        tables['students'].append({
            'id': s_id,
            'profile_id': p_id,
            'roll_no': roll,
            'department_id': dept_map.get(s_data.get('branch')),
            'section': s_data.get('section'),
            'cgpa': s_data.get('cgpa'),
            'backlogs': s_data.get('backlogs', 0),
            'gender': s_data.get('gender'),
            'minor_degree': s_data.get('minor_degree')
        })
        student_map[roll] = s_id

    # 5. Faculty
    print("Processing Faculty...")
    for f in faculty_data:
        p_id = str(uuid4())
        email = f.get('email') or f"{f['name'].lower().replace(' ', '.')}@faculty.vnr.edu.in"
        tables['profiles'].append({
            'id': p_id,
            'full_name': f['name'],
            'email': email,
            'user_type': 'faculty'
        })
        
        f_id = str(uuid4())
        tables['faculty'].append({
            'id': f_id,
            'profile_id': p_id,
            'department_id': dept_map.get(f['department']),
            'designation': f['designation'],
            'cabin': f['cabin']
        })
        faculty_map[f['name']] = f_id
        
        for day, sessions in f.get('schedule', {}).items():
            for session in sessions:
                time_range = session.split('(')[0].strip() if '(' in session else session
                subj = session.split('(')[1].replace(')', '').strip() if '(' in session else "General"
                tables['faculty_timetable'].append({
                    'id': str(uuid4()),
                    'faculty_id': f_id,
                    'day': day,
                    'time_range': time_range,
                    'subject': subj
                })

    # 6. Placement Drives
    print("Processing Placement Drives...")
    for p in placements_sample:
        c_name = next((c['name'] for c in companies_sample if c['id'] == p['company_id']), None)
        c_id = company_map.get(c_name)
        if not c_id: continue
        
        s_roll = next((s['roll_no'] for s in students_sample if s['id'] == p['student_id']), None)
        s_id = student_map.get(s_roll)
        if not s_id: continue
        
        d_id = str(uuid4())
        tables['placement_drives'].append({
            'id': d_id,
            'company_id': c_id,
            'drive_date': p['placement_date'][:10],
            'ctc': p['ctc_lpa'],
            'status': 'completed'
        })
        
        tables['placement_applications'].append({
            'id': str(uuid4()),
            'student_id': s_id,
            'drive_id': d_id,
            'status': 'selected'
        })
        tables['placement_offers'].append({
            'id': str(uuid4()),
            'student_id': s_id,
            'drive_id': d_id,
            'offered_ctc': p['ctc_lpa'],
            'accepted': True
        })

    # 7. Interview Experiences
    print("Processing Interview Experiences...")
    for corp in interview_exp_data['companies']:
        comp_name = corp['name']
        comp_id = company_map.get(comp_name)
        if not comp_id:
            comp_id = str(uuid4())
            tables['companies'].append({'id': comp_id, 'name': comp_name})
            company_map[comp_name] = comp_id
        
        for exp in corp['experiences']:
            e_id = str(uuid4())
            tables['interview_experiences'].append({
                'id': e_id,
                'company_id': comp_id,
                'overall_experience': f"Experience of {exp['candidate']}"
            })
            
            for idx, r in enumerate(exp['rounds']):
                r_id = str(uuid4())
                tables['interview_rounds'].append({
                    'id': r_id,
                    'experience_id': e_id,
                    'round_type': r['round'],
                    'round_order': idx + 1
                })
                
                for q in r['questions']:
                    tables['interview_questions'].append({
                        'id': str(uuid4()),
                        'round_id': r_id,
                        'question_text': q['question'],
                        'topic': ", ".join(q.get('tags', []))
                    })

    # Save to files
    print(f"Saving JSON files to {output_dir}...")
    for table_name, data in tables.items():
        with open(f"{output_dir}/{table_name}.json", 'w') as out_f:
            json.dump(data, out_f, indent=2)
            print(f"Created {table_name}.json ({len(data)} records)")

    print("\nGeneration completed successfully!")

if __name__ == "__main__":
    generate_json()
