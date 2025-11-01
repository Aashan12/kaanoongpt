from fastapi import APIRouter, Depends
from models.user import User
from routers.auth import get_current_user

router = APIRouter()

@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    """Get user profile - protected route"""
    return {
        "email": user.email,
        "full_name": user.full_name,
        "organization_type": user.organization_type,
        "organization_name": user.organization_name,
        "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "google_id": user.google_id,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

@router.put("/profile")
async def update_profile(
    full_name: str = None,
    organization_name: str = None,
    user: User = Depends(get_current_user)
):
    """Update user profile"""
    if full_name is not None:
        user.full_name = full_name
    if organization_name is not None:
        user.organization_name = organization_name
    
    from datetime import datetime
    user.updated_at = datetime.utcnow()
    await user.save()
    
    return {
        "message": "Profile updated successfully",
        "user": {
            "email": user.email,
            "full_name": user.full_name,
            "organization_name": user.organization_name
        }
    }

@router.get("/all-users")
async def get_all_users(current_user: User = Depends(get_current_user)):
    """Get all users (for debugging) - only for authenticated users"""
    users = await User.find_all().to_list()
    return {
        "total": len(users),
        "users": [
            {
                "email": u.email,
                "full_name": u.full_name,
                "organization_type": u.organization_type,
                "organization_name": u.organization_name,
                "google_id": u.google_id,
                "is_active": u.is_active,
                "is_email_verified": u.is_email_verified
            }
            for u in users
        ]
    }