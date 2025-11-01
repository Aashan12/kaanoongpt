from beanie import Document
from pydantic import EmailStr, Field
from typing import Optional
from datetime import datetime

class User(Document):
    # Basic Info
    email: EmailStr
    full_name: str = Field(default="User")
    date_of_birth: Optional[datetime] = None
    
    # Organization Type
    organization_type: str = Field(default="researcher")
    organization_name: Optional[str] = None
    
    # Authentication
    hashed_password: Optional[str] = None
    google_id: Optional[str] = None
    
    # Email Verification (OTP-based)
    is_email_verified: bool = False
    
    # Account Status
    is_active: bool = True
    is_superuser: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Settings:
        name = "users"
        
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "organization_type": "law_firm",
                "is_email_verified": True,
                "is_active": True
            }
        }


class PendingUser(Document):
    """
    Temporary storage for users pending OTP verification
    These documents will be deleted after verification or expiry
    """
    # User Data
    email: EmailStr
    full_name: str
    date_of_birth: datetime
    organization_type: str
    organization_name: Optional[str] = None
    hashed_password: str
    
    # OTP Data
    otp_code: str  # 6-digit OTP
    otp_created_at: datetime = Field(default_factory=datetime.utcnow)
    otp_attempts: int = Field(default=0)  # Track failed attempts
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "pending_users"
        
    def is_otp_expired(self, expiry_minutes: int = 10) -> bool:
        """Check if OTP has expired (default: 10 minutes)"""
        from datetime import timedelta
        expiry_time = self.otp_created_at + timedelta(minutes=expiry_minutes)
        return datetime.utcnow() > expiry_time
    
    def is_locked(self, max_attempts: int = 5) -> bool:
        """Check if account is locked due to too many failed attempts"""
        return self.otp_attempts >= max_attempts