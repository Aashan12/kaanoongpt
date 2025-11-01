from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional

class SignupRequest(BaseModel):
    """Request model for initial signup (Step 1)"""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    date_of_birth: str  # Format: YYYY-MM-DD
    organization_type: str  # "law_firm", "student", "researcher", etc.
    organization_name: Optional[str] = Field(None, max_length=200)
    password: str = Field(..., min_length=10)  # Updated to match frontend (10 chars minimum)
    confirm_password: str
    
    @field_validator('organization_type')
    @classmethod
    def validate_organization_type(cls, v):
        allowed = ['law_firm', 'corporate', 'government', 'ngo', 'individual', 'student', 'other']
        if v not in allowed:
            raise ValueError(f'organization_type must be one of: {", ".join(allowed)}')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, v):
        try:
            dob = datetime.strptime(v, '%Y-%m-%d')
            # Must be at least 18 years old
            age = (datetime.now() - dob).days / 365.25
            if age < 18:
                raise ValueError('You must be at least 18 years old')
            if age > 120:
                raise ValueError('Invalid date of birth')
            return v
        except ValueError as e:
            if 'does not match format' in str(e):
                raise ValueError('Date format must be YYYY-MM-DD')
            raise e

class VerifyOTPRequest(BaseModel):
    """Request model for OTP verification (Step 2)"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')
    
    @field_validator('otp')
    @classmethod
    def validate_otp(cls, v):
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        return v

class ResendOTPRequest(BaseModel):
    """Request model for resending OTP"""
    email: EmailStr

class LoginRequest(BaseModel):
    """Request model for login"""
    email: EmailStr
    password: str = Field(..., min_length=1)

class TokenResponse(BaseModel):
    """Response model for successful authentication"""
    access_token: str
    token_type: str = "bearer"
    user: dict

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    email: Optional[str] = None
    expires_in_minutes: Optional[int] = None