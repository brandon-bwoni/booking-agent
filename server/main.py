from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.mongodb import Database
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Booking Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    await Database.connect_db(os.getenv('MONGODB_URL'))

@app.on_event("shutdown")
async def shutdown_db_client():
    await Database.close_db()

@app.get("/")
async def root():
    return {"message": "Booking Agent API"}

@app.get("/api/now")
async def get_current_time():
    from datetime import datetime
    return {"timestamp": datetime.utcnow().isoformat()}