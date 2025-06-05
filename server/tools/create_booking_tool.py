from datetime import datetime
from enum import Enum
from typing import Optional
from typing import Union
from uuid import uuid4
from pydantic import BaseModel, Field
from langchain_core.messages import ToolMessage
from motor.motor_asyncio import AsyncIOMotorDatabase

# Booking models
from models import BookingStatus, BookingCreate, BookingInDB


async def create_and_save_booking(
    db: AsyncIOMotorDatabase,
    user_id: str, 
    description: str, 
    parsed_time: str
) -> Union[str, ToolMessage]:
    """
    Create and save a new booking to MongoDB.
    
    Args:
        db: MongoDB database instance
        user_id: The ID of the user making the booking
        description: Detailed description of the booking
        parsed_time: ISO format datetime string
        
    Returns:
        Union[str, ToolMessage]: Booking ID if successful, ToolMessage if issues
    """
    # Initialize bookings collection with unique index
    collection = db["bookings"]
    await collection.create_index(
        [("user_id", 1), ("timestamp", 1)],
        unique=True,
        name="user_timestamp_unique"
    )

    # Parse the booking time
    booking_time = datetime.fromisoformat(parsed_time)
    current_time = datetime.utcnow()

    # Check for existing booking
    if await collection.find_one({
        "user_id": user_id, 
        "timestamp": booking_time
    }):
        return ToolMessage(
            name="create_booking",
            content="There is already a booking scheduled for this time slot. Would you like to choose a different time?",
            parameters={}
        )

    # Create booking object
    booking = BookingCreate(
        user_id=user_id,
        description=description.strip(),
        timestamp=booking_time,
        created_at=current_time,
        updated_at=current_time
    )

    # Save to database
    result = await collection.insert_one(booking.model_dump())
    
    return str(result.inserted_id)