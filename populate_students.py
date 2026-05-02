import asyncio
import uuid
import random
from sqlalchemy import select
from core.db import async_session
from models.student import Student
from models.profile import Profile
from models.department import Department

async def populate():
    async with async_session() as db:
        # Get departments
        deps_result = await db.execute(select(Department))
        deps = deps_result.scalars().all()
        if not deps:
            print("No departments found. Creating sample departments.")
            for dname in ["CSE", "IT", "ECE", "EEE", "MECH"]:
                db.add(Department(id=uuid.uuid4(), name=dname))
            await db.commit()
            deps = (await db.execute(select(Department))).scalars().all()

        # Check existing students
        existing = (await db.execute(select(Student))).scalars().all()
        if len(existing) >= 10:
            print(f"Found {len(existing)} students. Skipping.")
            return

        first_names = ["Arjun", "Deepa", "Vikram", "Sanya", "Rahul", "Anjali", "Karan", "Pooja", "Rohan", "Sneha"]
        last_names = ["Sharma", "Verma", "Gupta", "Malhotra", "Joshi", "Reddy", "Patel", "Iyer", "Nair", "Singh"]
        branches = ["CSE", "IT", "ECE", "EEE", "MECH"]
        companies = ["Google", "Microsoft", "Amazon", "TCS", "Infosys", None]

        for i in range(20):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            full_name = f"{fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}{i}@vnr.edu"
            
            # Create Profile
            profile_id = uuid.uuid4()
            db.add(Profile(id=profile_id, full_name=full_name, email=email, user_type="student"))
            
            # Create Student
            dept = random.choice(deps)
            placement_status = "placed" if random.random() > 0.4 else "unplaced"
            
            student = Student(
                id=uuid.uuid4(),
                roll_no=f"20XJ1A{501 + i:02d}",
                profile_id=profile_id,
                department_id=dept.id,
                cgpa=round(random.uniform(7.0, 9.8), 2),
                placement_status=placement_status,
                highest_package=round(random.uniform(4.0, 45.0), 1) if placement_status == "placed" else 0.0,
                minor_degree=random.choice(["AI/ML", "Cybersecurity", "Data Science", None]) if random.random() > 0.7 else None
            )
            db.add(student)
            print(f"Added Student: {full_name} ({placement_status})")

        await db.commit()
        print("Successfully populated sample students.")

if __name__ == "__main__":
    asyncio.run(populate())
