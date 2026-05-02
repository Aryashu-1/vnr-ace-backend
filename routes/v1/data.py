from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from schemas.data import StudentResponse, CompanyResponse
from models.student import Student
from models.company import Company
from models.department import Department

router = APIRouter(prefix="/data", tags=["Data"])

from sqlalchemy.orm import joinedload

@router.post("/seed-data")
async def seed_data_v2(db: AsyncSession = Depends(get_db)):
    import uuid
    import random
    from datetime import datetime, timedelta
    from sqlalchemy import select, delete
    from models.student import Student
    from models.profile import Profile
    from models.department import Department
    from models.placement_offer_v2 import PlacementOfferV2
    from models.placement_drive import PlacementDrive
    from models.company import Company
    
    try:
        # Clear existing seeded data if needed (optional, but good for clean state)
        # For now, let's just add new ones
        
        # Get or create departments
        deps_result = await db.execute(select(Department))
        deps = deps_result.scalars().all()
        if not deps:
            for dname in ["CSE", "IT", "ECE", "EEE", "MECH"]:
                db.add(Department(id=uuid.uuid4(), name=dname))
            await db.flush()
            deps = (await db.execute(select(Department))).scalars().all()

        # Create multiple companies
        company_names = ["GlobalTech", "DataSystems", "CloudNexus", "InnovaSolutions", "CyberGuard"]
        comps = []
        for cname in company_names:
            comp_result = await db.execute(select(Company).where(Company.name == cname))
            comp = comp_result.scalar_one_or_none()
            if not comp:
                comp = Company(id=uuid.uuid4(), name=cname, sector="Technology")
                db.add(comp)
            comps.append(comp)
        await db.flush()

        # Create drives for different years
        drives = []
        years = [2024, 2025, 2026]
        for year in years:
            for i in range(2):
                drive_date = datetime(year, random.randint(1, 12), random.randint(1, 28)).date()
                drive = PlacementDrive(
                    id=uuid.uuid4(),
                    company_id=random.choice(comps).id,
                    role=f"Phase {i+1} Recruitment",
                    status="completed",
                    drive_date=drive_date
                )
                db.add(drive)
                drives.append(drive)
        await db.flush()

        first_names = ["Arjun", "Deepa", "Vikram", "Sanya", "Rahul", "Anjali", "Karan", "Pooja", "Rohan", "Sneha", "Aditya", "Meera", "Yash", "Ishani", "Kabir"]
        last_names = ["Sharma", "Verma", "Gupta", "Malhotra", "Joshi", "Reddy", "Patel", "Iyer", "Nair", "Singh"]
        
        for i in range(50):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            full_name = f"{fname} {lname}"
            email = f"seed.{fname.lower()}.{lname.lower()}.{uuid.uuid4().hex[:4]}@vnr.edu"
            
            profile_id = uuid.uuid4()
            db.add(Profile(id=profile_id, full_name=full_name, email=email, user_type="student"))
            
            # Weighted placement based on year (more in 2026 for demo)
            is_placed = random.random() > 0.3
            salary = round(random.uniform(8.0, 52.0), 1) if is_placed else 0.0
            
            student_id = uuid.uuid4()
            student = Student(
                id=student_id,
                roll_no=f"21R01A{800 + i:02d}",
                profile_id=profile_id,
                department_id=random.choice(deps).id,
                cgpa=round(random.uniform(7.0, 9.9), 2),
                placement_status="placed" if is_placed else "unplaced",
                highest_package=salary
            )
            db.add(student)
            await db.flush() # Ensure student is present for FK
            
            if is_placed:
                # Add 1-2 unique offers
                num_offers = random.randint(1, 2)
                selected_drives = random.sample(drives, k=min(num_offers, len(drives)))
                for drive in selected_drives:
                    db.add(PlacementOfferV2(
                        id=uuid.uuid4(),
                        student_id=student.id,
                        drive_id=drive.id,
                        offered_ctc=round(random.uniform(salary-2, salary+2), 1),
                        accepted=True
                    ))

        await db.commit()
        return {"status": "success", "message": "50 students and historical drives seeded"}
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        await db.rollback()
        return {"status": "error", "message": str(e)}

@router.get("/students", response_model=List[StudentResponse])
async def get_students(
    search: Optional[str] = None,
    branch: Optional[str] = None,
    placed: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import or_
    from models.profile import Profile
    query = select(Student).options(
        joinedload(Student.profile),
        joinedload(Student.department_rel)
    )
    
    if search:
        query = query.join(Profile).filter(
            or_(
                Student.roll_no.ilike(f"%{search}%"),
                Profile.full_name.ilike(f"%{search}%")
            )
        )
    
    if branch and branch != "all":
        query = query.join(Department).filter(Department.name == branch)
        
    if placed and placed != "all":
        is_placed = placed.lower() == "true"
        query = query.filter(Student.placement_status == ("placed" if is_placed else "unplaced"))

    result = await db.execute(query)
    students = result.scalars().unique().all()
    
    student_list = []
    for s in students:
        # Create a dictionary for the response
        s_data = {
            "id": s.id,
            "rollNumber": s.roll_no,
            "name": s.full_name, # This uses the @property on the Student model
            "gender": s.gender,
            "branch": s.branch, # This uses the @property on the Student model
            "cgpa": s.cgpa,
            "minor_degree": s.minor_degree,
            "intern_status": s.intern_status,
            "placed": s.placement_status == "placed",
            "company": getattr(s, 'company', None), # Fallback if not directly on student
            "salary": s.highest_package,
            "created_at": s.created_at
        }
        student_list.append(s_data)
        
    return student_list

@router.get("/companies", response_model=List[CompanyResponse])
async def get_companies(
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Company).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

