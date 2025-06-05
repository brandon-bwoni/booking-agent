from datetime import datetime
from typing import Union
from uuid import uuid4
from pydantic import BaseModel, Field
from langchain_core.messages import ToolMessage
from enum import Enum
from typing import Optional

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

def create_booking(
    user_id: str, 
    description: str, 
    parsed_time: str
) -> Booking:
    """
    Create a new booking using parsed time.
    
    Args:
        user_id: The ID of the user making the booking
        description: Detailed description of the booking
        parsed_time: ISO format datetime string
        
    Returns:
        Booking: A new booking object
    """
    current_time = datetime.utcnow()
    booking_time = datetime.fromisoformat(parsed_time)

    booking = Booking(
        user_id=user_id,
        description=description.strip(),
        timestamp=booking_time,
        created_at=current_time,
        updated_at=current_time
    )
    
    return booking