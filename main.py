import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.user import User, PendingUser  # Import both models
from routers.auth import router as auth_router
from routers.protected import router as protected_router
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="KaanoonGPT",
    description="API with Google OAuth authentication"
)

# CORS Configuration - Get from environment variable
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
# Split by comma if multiple URLs
origins = [url.strip() for url in FRONTEND_URL.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use environment variable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """Initialize database connection on startup"""
    try:
        client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
        await init_beanie(
            database=client.kaanoongpt, 
            document_models=[User, PendingUser]  # Register both models
        )
        print("✅ Database connected successfully")
        print(f"✅ CORS enabled for: {origins}")  # Log allowed origins
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "KaanoonGPT API is running"
    }

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(protected_router, prefix="/api", tags=["Protected"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)