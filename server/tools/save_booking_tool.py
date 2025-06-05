from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from langchain_core.messages import ToolMessage

async def save_booking_to_db_async(
    db: AsyncIOMotorDatabase, 
    booking: Dict[str, Any]
) -> str:
    """
    Save a confirmed booking to MongoDB.
    
    Args:
        db: MongoDB database instance
        booking: Pre-validated booking data from agent conversation
        
    Returns:
        str: Booking ID for successful save
    """
    # Initialize bookings collection with unique index
    collection = db["bookings"]
    await collection.create_index(
        [("user_id", 1), ("timestamp", 1)],
        unique=True,
        name="user_timestamp_unique"
    )
    
    # Attempt to save the booking
    if await collection.find_one({"user_id": booking["user_id"], "timestamp": booking["timestamp"]}):
        return ToolMessage(
            name="save_booking",
            content="There is already a booking scheduled for this time slot. Would you like to choose a different time?",
            parameters={}
        )
    
    # Insert the new booking
    result = await collection.insert_one(booking)
    return str(result.inserted_id)