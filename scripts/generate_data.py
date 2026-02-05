import pandas as pd
import random

def generate_data():
    names = ["Aarav", "Bhavna", "Chirag", "Divya", "Esha", "Farhan", "Gauri", "Harsh", "Ishaan", "Jiya", 
             "Karthik", "Lakshmi", "Manish", "Neha", "Om", "Priya", "Rahul", "Sneha", "Tanvi", "Varun",
             "Rohan", "Sanya", "Vikram", "Ananya", "Arjun", "Zara", "Vihaan", "Myra", "Reyansh", "Aditi"]
    
    departments = ["CSE", "ECE", "IT"]
    years = [1, 2, 3, 4]
    
    data = []
    for i, name in enumerate(names):
        dept = random.choice(departments)
        year = random.choice(years)
        
        # Correlate attendance and GPA slightly for realism
        attendance = random.randint(40, 98)
        if attendance > 85:
            gpa = round(random.uniform(7.5, 9.8), 2)
        elif attendance > 70:
            gpa = round(random.uniform(6.0, 8.5), 2)
        else:
            gpa = round(random.uniform(4.0, 6.5), 2)
            
        data.append({
            "id": 101 + i,
            "name": name,
            "branch": dept,
            "year": year,
            "attendance_pct": attendance,
            "cumulative_gpa": gpa,
            "email": f"{name.lower()}@vnr.edu.in"
        })
        
    df = pd.DataFrame(data)
    import os
    # Script is in backend/scripts/generate_data.py
    # Data should be in backend/data/student_data.xlsx
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "../data/student_data.xlsx")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    df.to_excel(file_path, index=False)
    print(f"Generated {len(data)} records at {file_path}")

if __name__ == "__main__":
    generate_data()
