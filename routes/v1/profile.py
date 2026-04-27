import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user
from models.student import Student
from models.placement_application import PlacementApplication
from schemas.profile import ProfilePlacementStatsResponse, Recommendation

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("/placement-stats", response_model=ProfilePlacementStatsResponse)
async def get_profile_placement_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Get student record
    student = await db.scalar(select(Student).where(Student.profile_id == current_user.id))
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    # Get applications count
    total_apps = await db.scalar(
        select(func.count(PlacementApplication.id))
        .where(PlacementApplication.student_id == student.id)
    )

    # Get rejections count
    rejections = await db.scalar(
        select(func.count(PlacementApplication.id))
        .where(
            PlacementApplication.student_id == student.id,
            PlacementApplication.status == "rejected"
        )
    )

    status = "on_track"
    recommendations = []

    if rejections >= 10:
        status = "needs_attention"
        recommendations = [
            Recommendation(
                topic="Data Structures & Algorithms",
                detail="Your recent interview feedback suggests a need to strengthen Graph theory and Dynamic Programming concepts.",
                icon="code"
            ),
            Recommendation(
                topic="System Design",
                detail="Focus on scalability and high-level architecture for product-based company rounds.",
                icon="layers"
            ),
            Recommendation(
                topic="Mock Interviews",
                detail="Schedule a session with our placement coaches to improve your communication and problem-solving explanation.",
                icon="users"
            )
        ]
    elif rejections >= 5:
        status = "improving"
        recommendations = [
            Recommendation(
                topic="Aptitude & Logical Reasoning",
                detail="Continue practicing quantitative aptitude to clear the first rounds of upcoming companies.",
                icon="brain"
            )
        ]

    return ProfilePlacementStatsResponse(
        total_applications=total_apps or 0,
        rejections=rejections or 0,
        status=status,
        recommendations=recommendations
    )
