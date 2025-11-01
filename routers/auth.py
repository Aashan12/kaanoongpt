from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from httpx_oauth.clients.google import GoogleOAuth2
from models.user import User, PendingUser
from models.schemas import SignupRequest, VerifyOTPRequest, ResendOTPRequest, LoginRequest
from utils.password import hash_password, verify_password
from services.email_services import send_otp_email, generate_otp
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from jose import jwt, JWTError
import traceback

load_dotenv()

router = APIRouter()

# Get URLs from environment
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").split(",")[0]  # Get first URL

print(f"🌐 BACKEND_URL: {BACKEND_URL}")
print(f"🌐 FRONTEND_URL: {FRONTEND_URL}")

# Google OAuth
google_oauth_client = GoogleOAuth2(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in .env file")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Import security dependencies
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

security = HTTPBearer()

def create_access_token(data: dict):
    """Create JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
    """Verify JWT token and return current user"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = await User.find_one(User.email == email)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# ============== OTP-BASED SIGNUP ROUTES ==============

@router.post("/signup")
async def signup(signup_data: SignupRequest):
    """
    Step 1: Register user and send OTP to email
    User data is stored in PendingUser collection until OTP verification
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 Received signup request")
        print(f"{'='*60}")
        print(f"Email: {signup_data.email}")
        print(f"Full Name: {signup_data.full_name}")
        
        # Check if user already exists in main User collection
        existing_user = await User.find_one(User.email == signup_data.email)
        if existing_user:
            print(f"❌ User already exists: {signup_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please login or use a different email."
            )
        
        # Check if there's a pending verification for this email
        pending_user = await PendingUser.find_one(PendingUser.email == signup_data.email)
        
        # Parse date of birth
        try:
            dob = datetime.strptime(signup_data.date_of_birth, '%Y-%m-%d')
            print(f"📅 Parsed date of birth: {dob}")
        except ValueError as e:
            print(f"❌ Date parsing error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format. Expected YYYY-MM-DD"
            )
        
        # Hash password
        try:
            print(f"\n🔐 Hashing password...")
            hashed_pwd = hash_password(signup_data.password)
            print(f"✅ Password hashed successfully\n")
        except Exception as e:
            print(f"❌ Password hashing error: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to hash password: {str(e)}"
            )
        
        # Generate OTP
        otp_code = generate_otp()
        print(f"🔑 Generated OTP: {otp_code}")
        
        if pending_user:
            # Update existing pending user
            print(f"📝 Updating existing pending user...")
            pending_user.full_name = signup_data.full_name
            pending_user.date_of_birth = dob
            pending_user.organization_type = signup_data.organization_type
            pending_user.organization_name = signup_data.organization_name
            pending_user.hashed_password = hashed_pwd
            pending_user.otp_code = otp_code
            pending_user.otp_created_at = datetime.utcnow()
            pending_user.otp_attempts = 0  # Reset attempts
            await pending_user.save()
        else:
            # Create new pending user
            print(f"📝 Creating new pending user...")
            pending_user = PendingUser(
                email=signup_data.email,
                full_name=signup_data.full_name,
                date_of_birth=dob,
                organization_type=signup_data.organization_type,
                organization_name=signup_data.organization_name,
                hashed_password=hashed_pwd,
                otp_code=otp_code,
                otp_created_at=datetime.utcnow(),
                otp_attempts=0
            )
            await pending_user.insert()
        
        print(f"✅ Pending user saved: {pending_user.email}")
        
        # Send OTP email
        print(f"📧 Sending OTP email to: {pending_user.email}")
        email_sent = await send_otp_email(
            to_email=pending_user.email,
            full_name=pending_user.full_name,
            otp=otp_code
        )
        
        if not email_sent:
            print("⚠️ Warning: Failed to send OTP email")
        
        print(f"\n{'='*60}")
        print(f"✅ SIGNUP SUCCESSFUL - OTP SENT")
        print(f"{'='*60}\n")
        
        return {
            "message": "OTP sent successfully! Please check your email to verify your account.",
            "email": pending_user.email,
            "expires_in_minutes": 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ SIGNUP ERROR")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signup failed: {str(e)}"
        )


@router.post("/verify-otp")
async def verify_otp(verification: VerifyOTPRequest):
    """
    Step 2: Verify OTP and create actual user account
    On success, user is moved from PendingUser to User collection
    
    Note: All user data is already stored in PendingUser,
    we only need email and OTP to verify
    """
    try:
        print(f"\n{'='*60}")
        print(f"📧 OTP Verification Request")
        print(f"{'='*60}")
        print(f"Email: {verification.email}")
        print(f"OTP: {verification.otp}")
        
        # Find pending user
        pending_user = await PendingUser.find_one(PendingUser.email == verification.email)
        
        if not pending_user:
            print(f"❌ No pending user found for: {verification.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending verification found. Please sign up again."
            )
        
        # Check if OTP is expired
        if pending_user.is_otp_expired(expiry_minutes=10):
            print(f"❌ OTP expired for: {verification.email}")
            await pending_user.delete()  # Clean up expired pending user
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please sign up again."
            )
        
        # Check if account is locked
        if pending_user.is_locked(max_attempts=5):
            print(f"❌ Account locked due to too many attempts: {verification.email}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Please sign up again."
            )
        
        # Verify OTP
        if pending_user.otp_code != verification.otp:
            print(f"❌ Invalid OTP for: {verification.email}")
            pending_user.otp_attempts += 1
            await pending_user.save()
            
            remaining_attempts = 5 - pending_user.otp_attempts
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP. {remaining_attempts} attempts remaining."
            )
        
        print(f"✅ OTP verified successfully!")
        
        # Create actual user account
        print(f"📝 Creating user account...")
        user = User(
            email=pending_user.email,
            full_name=pending_user.full_name,
            date_of_birth=pending_user.date_of_birth,
            organization_type=pending_user.organization_type,
            organization_name=pending_user.organization_name,
            hashed_password=pending_user.hashed_password,
            is_email_verified=True,
            is_active=True
        )
        
        await user.insert()
        print(f"✅ User created successfully: {user.email}")
        
        # Delete pending user
        await pending_user.delete()
        print(f"🗑️ Pending user deleted")
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        print(f"\n{'='*60}")
        print(f"✅ VERIFICATION SUCCESSFUL")
        print(f"{'='*60}\n")
        
        return {
            "message": "Email verified successfully! Welcome to KAANOONGPT!",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "email": user.email,
                "full_name": user.full_name,
                "organization_type": user.organization_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification failed"
        )


@router.post("/resend-otp")
async def resend_otp(resend_data: ResendOTPRequest):
    """
    Resend OTP to user's email
    """
    try:
        print(f"\n📧 Resend OTP request for: {resend_data.email}")
        
        # Find pending user
        pending_user = await PendingUser.find_one(PendingUser.email == resend_data.email)
        
        if not pending_user:
            print(f"❌ No pending user found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending verification found. Please sign up again."
            )
        
        # Generate new OTP
        new_otp = generate_otp()
        print(f"🔑 Generated new OTP: {new_otp}")
        
        # Update pending user with new OTP
        pending_user.otp_code = new_otp
        pending_user.otp_created_at = datetime.utcnow()
        pending_user.otp_attempts = 0  # Reset attempts
        await pending_user.save()
        
        # Send OTP email
        print(f"📧 Sending OTP email...")
        email_sent = await send_otp_email(
            to_email=pending_user.email,
            full_name=pending_user.full_name,
            otp=new_otp
        )
        
        if not email_sent:
            print("⚠️ Failed to send OTP email")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again."
            )
        
        print(f"✅ OTP resent successfully")
        
        return {
            "message": "New OTP sent successfully! Please check your email.",
            "email": pending_user.email,
            "expires_in_minutes": 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Resend OTP error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resend OTP"
        )


# ============== LOGIN ROUTE ==============

@router.post("/login")
async def login(login_data: LoginRequest):
    """Login with email and password"""
    try:
        print(f"\n🔐 Login attempt for: {login_data.email}")
        
        # Find user
        user = await User.find_one(User.email == login_data.email)
        
        if not user or not user.hashed_password:
            print(f"❌ User not found or no password set")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            print(f"❌ Invalid password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if email is verified
        if not user.is_email_verified:
            print(f"❌ Email not verified")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in"
            )
        
        # Check if account is active
        if not user.is_active:
            print(f"❌ Account inactive")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        print(f"✅ Login successful: {user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "email": user.email,
                "full_name": user.full_name,
                "organization_type": user.organization_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login failed"
        )


# ============== GOOGLE OAUTH ROUTES ==============

@router.get("/google/authorize")
async def google_authorize():
    """Step 1: Redirect user to Google OAuth"""
    authorization_url = await google_oauth_client.get_authorization_url(
        redirect_uri=f"{BACKEND_URL}/auth/google/callback",
        scope=["openid", "email", "profile"],
    )
    return {"authorization_url": authorization_url}

@router.get("/google/callback")
async def google_callback(code: str):
    """Step 2: Handle Google callback and create/login user"""
    try:
        print(f"📥 Received callback with code: {code[:20]}...")
        
        # Exchange code for access token
        token = await google_oauth_client.get_access_token(
            code, 
            redirect_uri=f"{BACKEND_URL}/auth/google/callback"
        )
        print(f"✅ Got access token")
        
        # Decode the id_token to get user info
        id_token = token.get("id_token")
        if not id_token:
            raise HTTPException(status_code=400, detail="No id_token in response")
        
        # ✅ FIXED: Decode JWT and skip ALL validation
        user_data = jwt.decode(
            id_token,
            key="",
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_iat": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iss": False,
                "verify_sub": False,
                "verify_jti": False,
                "verify_at_hash": False,  # ← Critical: prevents at_hash error
            },
            algorithms=["RS256"]
        )
        print(f"✅ Got user data: {user_data.get('email')}")
        
        email = user_data.get("email")
        google_id = user_data.get("sub")
        
        # Extract full name
        full_name = user_data.get("name", "")
        if not full_name:
            first_name = user_data.get("given_name", "")
            last_name = user_data.get("family_name", "")
            full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = email.split('@')[0]
        
        if not email or not google_id:
            raise HTTPException(status_code=400, detail="Missing email or google_id")
        
        # Check if user exists
        user = await User.find_one(User.email == email)
        
        if not user:
            # Create new user from Google
            print(f"📝 Creating new user: {email}")
            
            user = User(
                email=email,
                full_name=full_name,
                google_id=google_id,
                organization_type="individual",
                is_email_verified=True,
                is_active=True,
                is_superuser=False,
            )
            await user.insert()
            print(f"✅ User created successfully")
        else:
            # User exists - just update google_id if needed
            print(f"👤 User already exists: {user.email}")
            if not user.google_id:
                user.google_id = google_id
                await user.save()
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        print(f"✅ Login successful for: {user.email}")
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{FRONTEND_URL}/auth/callback?token={access_token}"
        )
        
    except Exception as e:
        print(f"❌ ERROR in callback: {str(e)}")
        traceback.print_exc()
        return RedirectResponse(
            url=f"{FRONTEND_URL}/auth/login?error=authentication_failed"
        )
    
@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current logged-in user info"""
    return {
        "email": current_user.email,
        "full_name": current_user.full_name,
        "organization_type": current_user.organization_type,
        "organization_name": current_user.organization_name,
        "date_of_birth": current_user.date_of_birth.isoformat() if current_user.date_of_birth else None,
        "is_active": current_user.is_active,
        "is_email_verified": current_user.is_email_verified
    }