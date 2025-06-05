from datetime import datetime
from typing import Union
from uuid import uuid4
from pydantic import BaseModel, Field
from langchain_core.messages import ToolMessage
from enum import Enum
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class Booking(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=10, max_length=500)
    timestamp: datetime
    status: BookingStatus = BookingStatus.PENDING
    created_at: datetime
    updated_at: datetime
    cancellation_reason: Optional[str] = None

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
    booking = Booking(
        user_id=user_id,
        description=description.strip(),
        timestamp=booking_time,
        created_at=current_time,
        updated_at=current_time
    )

    # Save to database
    result = await collection.insert_one(booking.model_dump())
    
    return str(result.inserted_id)