
import asyncio
import uuid
import random
from sqlalchemy import select
from core.db import engine, async_session
from models.student import Student
from models.profile import Profile
from models.department import Department
from models.placement_offer_v2 import PlacementOfferV2
from models.placement_drive import PlacementDrive
from models.company import Company

async def boost_placements():
    async with async_session() as db:
        # Get departments
        deps_result = await db.execute(select(Department))
        deps = deps_result.scalars().all()
        if not deps:
            print("No departments found.")
            return

        # Get companies
        comp_result = await db.execute(select(Company))
        comps = comp_result.scalars().all()
        if not comps:
            print("No companies found. Creating a sample company.")
            comp = Company(id=uuid.uuid4(), name="TechCorp", sector="IT")
            db.add(comp)
            await db.commit()
            comps = [comp]

        # Get/Create a placement drive
        drive_result = await db.execute(select(PlacementDrive))
        drives = drive_result.scalars().all()
        if not drives:
            print("No drives found. Creating a sample drive.")
            drive = PlacementDrive(
                id=uuid.uuid4(),
                company_id=comps[0].id,
                title="Grand Placement Drive 2026",
                status="completed"
            )
            db.add(drive)
            await db.commit()
            drives = [drive]

        first_names = ["Arjun", "Deepa", "Vikram", "Sanya", "Rahul", "Anjali", "Karan", "Pooja", "Rohan", "Sneha", "Aditya", "Meera", "Yash", "Ishani"]
        last_names = ["Sharma", "Verma", "Gupta", "Malhotra", "Joshi", "Reddy", "Patel", "Iyer", "Nair", "Singh", "Kulkarni", "Deshmukh", "Choudhury"]
        
        print("Adding 30 more students with high placement rate...")
        
        for i in range(30):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            full_name = f"{fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}.boost{i}@vnr.edu"
            
            # Create Profile
            profile_id = uuid.uuid4()
            db.add(Profile(id=profile_id, full_name=full_name, email=email, user_type="student"))
            
            # Create Student
            dept = random.choice(deps)
            roll_no = f"21XJ1A{601 + i:02d}"
            
            # Higher placement probability for "boost" students
            is_placed = random.random() > 0.3
            placement_status = "placed" if is_placed else "unplaced"
            highest_package = round(random.uniform(12.0, 48.0), 1) if is_placed else 0.0
            
            student_id = uuid.uuid4()
            student = Student(
                id=student_id,
                roll_no=roll_no,
                profile_id=profile_id,
                department_id=dept.id,
                cgpa=round(random.uniform(8.0, 9.9), 2),
                placement_status=placement_status,
                highest_package=highest_package,
                minor_degree=random.choice(["AI/ML", "Data Science", None]) if random.random() > 0.5 else None
            )
            db.add(student)
            
            if is_placed:
                # Add a placement offer
                offer = PlacementOfferV2(
                    id=uuid.uuid4(),
                    student_id=student_id,
                    drive_id=random.choice(drives).id,
                    offered_ctc=highest_package,
                    accepted=True
                )
                db.add(offer)

            print(f"Added: {full_name} | {roll_no} | {placement_status} ({highest_package} LPA)")

        await db.commit()
        print("✓ Database boosted with fresh placement data!")

if __name__ == "__main__":
    asyncio.run(boost_placements())
