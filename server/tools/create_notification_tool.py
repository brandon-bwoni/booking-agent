from datetime import datetime
from typing import Optional, Literal
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.messages import ToolMessage
from bson import ObjectId
from enum import Enum
from pydantic import BaseModel, Field

class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"

class BookingUpdate(BaseModel):
    status: BookingStatus
    new_time: Optional[datetime] = None
    reason: Optional[str] = Field(None, min_length=5, max_length=500)

async def update_booking_status_tool(
    db: AsyncIOMotorDatabase,
    booking_id: str,
    update: BookingUpdate
) -> ToolMessage:
    """
    Updates a booking's status with audit trail and validation.
    
    Args:
        db: Database connection
        booking_id: ID of booking to update
        update: BookingUpdate model with new status and details
    """
    # Validate booking exists
    booking = await db["bookings"].find_one(
        {"_id": ObjectId(booking_id)},
        projection={"status": 1, "provider_id": 1}
    )
    
    if not booking:
        return ToolMessage(
            name="update_booking",
            content=f"No booking found with ID: {booking_id}",
            parameters={}
        )

    # Handle rescheduling
    if update.status == BookingStatus.RESCHEDULED:
        if not update.new_time:
            return ToolMessage(
                name="update_booking",
                content="New time required for rescheduling",
                parameters={
                    "new_time": {
                        "type": "string",
                        "description": "ISO format datetime for new appointment"
                    }
                }
            )
        
        # Check slot availability
        slot_available = await check_slot_availability(
            db, 
            booking["provider_id"],
            update.new_time,
            exclude_booking_id=booking_id
        )
        
        if not slot_available:
            return ToolMessage(
                name="update_booking",
                content="Requested time slot is not available",
                parameters={}
            )

    # Create audit entry
    audit_entry = {
        "booking_id": booking_id,
        "previous_status": booking["status"],
        "new_status": update.status,
        "changed_at": datetime.utcnow(),
        "reason": update.reason,
        "new_time": update.new_time
    }

    # Prepare update
    update_fields = {
        "status": update.status,
        "updated_at": datetime.utcnow()
    }

    if update.status == BookingStatus.CANCELLED:
        update_fields["cancellation_reason"] = update.reason or "No reason provided"
    elif update.status == BookingStatus.RESCHEDULED:
        update_fields["timestamp"] = update.new_time

    # Execute update and audit in transaction
    async with await db.client.start_session() as session:
        async with session.start_transaction():
            await db["bookings"].update_one(
                {"_id": ObjectId(booking_id)},
                {"$set": update_fields},
                session=session
            )
            await db["booking_audits"].insert_one(audit_entry, session=session)

    # Build response message
    status_messages = {
        BookingStatus.CANCELLED: f"cancelled. Reason: {update.reason}",
        BookingStatus.RESCHEDULED: f"rescheduled to {update.new_time.isoformat()}",
        BookingStatus.CONFIRMED: "confirmed",
        BookingStatus.PENDING: "marked as pending"
    }

    return ToolMessage(
        name="update_booking",
        content=f"Booking {booking_id} has been {status_messages[update.status]}",
        parameters={}
    )

async def check_slot_availability(
    db: AsyncIOMotorDatabase,
    provider_id: str,
    requested_time: datetime,
    exclude_booking_id: Optional[str] = None
) -> bool:
    """Check if a time slot is available."""
    query = {
        "provider_id": provider_id,
        "timestamp": requested_time,
        "status": {"$in": [BookingStatus.CONFIRMED, BookingStatus.PENDING]}
    }
    
    if exclude_booking_id:
        query["_id"] = {"$ne": ObjectId(exclude_booking_id)}
    
    existing = await db["bookings"].find_one(query, projection={"_id": 1})
    return existing is None