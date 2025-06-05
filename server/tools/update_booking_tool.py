from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.messages import ToolMessage
from bson import ObjectId
from models import BookingStatus, BookingUpdate


async def update_booking_status(
    db: AsyncIOMotorDatabase,
    booking_id: str,
    update: BookingUpdate
) -> ToolMessage:
    """
    Updates a booking's status with audit trail.
    
    Args:
        db: Database connection
        booking_id: ID of booking to update
        update: BookingUpdate model with new status
    """
    # Validate booking exists
    booking = await db["bookings"].find_one(
        {"_id": ObjectId(booking_id)},
        projection={"status": 1}
    )
    
    if not booking:
        return ToolMessage(
            name="update_booking",
            content=f"No booking found with ID: {booking_id}",
            parameters={}
        )

    # Create audit entry
    audit_entry = {
        "booking_id": booking_id,
        "previous_status": booking["status"],
        "new_status": update.status,
        "changed_at": datetime.utcnow(),
        "reason": update.reason
    }

    # Prepare update
    update_fields = {
        "status": update.status,
        "updated_at": datetime.utcnow()
    }

    if update.status == BookingStatus.CANCELLED:
        update_fields["cancellation_reason"] = update.reason or "No reason provided"

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
        BookingStatus.CONFIRMED: "confirmed",
        BookingStatus.PENDING: "pending"
    }

    return ToolMessage(
        name="update_booking",
        content=f"Booking {booking_id} has been {status_messages[update.status]}",
        parameters={}
    )