from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.messages import ToolMessage
from zoneinfo import ZoneInfo

# Configuration
class SlotConfig:
    DURATION_MINUTES: int = 30
    BUFFER_MINUTES: int = 10
    MAX_DAYS_AHEAD: int = 30
    DEFAULT_TIMEZONE: str = "UTC"

async def get_provider_schedule(
    db: AsyncIOMotorDatabase, 
    provider_id: str,
    date: str
) -> Dict[str, Any]:
    """Fetch provider's schedule with caching."""
    cache_key = f"schedule:{provider_id}:{date}"
    print(cache_key)
    
    # Check cache first
    provider = await db["providers"].find_one(
        {"_id": provider_id},
        projection={"schedule": 1, "timezone": 1}
    )
    
    if not provider:
        return {}
        
    schedule = provider.get("schedule", {})
    schedule["timezone"] = provider.get("timezone", SlotConfig.DEFAULT_TIMEZONE)
    return schedule

async def generate_available_slots(
    schedule: Dict[str, Any],
    date: str,
    existing_bookings: List[datetime]
) -> List[datetime]:
    """Generate available slots efficiently."""
    if not schedule.get("working_hours"):
        return []

    # Convert times to provider's timezone
    tz = ZoneInfo(schedule.get("timezone", SlotConfig.DEFAULT_TIMEZONE))
    start = datetime.fromisoformat(f"{date}T{schedule['working_hours']['start']}").replace(tzinfo=tz)
    end = datetime.fromisoformat(f"{date}T{schedule['working_hours']['end']}").replace(tzinfo=tz)
    
    # Pre-calculate break periods
    breaks = [
        (
            datetime.fromisoformat(f"{date}T{b['start']}").replace(tzinfo=tz),
            datetime.fromisoformat(f"{date}T{b['end']}").replace(tzinfo=tz)
        )
        for b in schedule.get("breaks", [])
    ]
    
    # Generate slots efficiently
    slots = []
    current = start
    slot_delta = timedelta(minutes=SlotConfig.DURATION_MINUTES)
    buffer_delta = timedelta(minutes=SlotConfig.BUFFER_MINUTES)
    
    while current + slot_delta <= end:
        # Skip if slot is during break
        if not any(b_start <= current < b_end for b_start, b_end in breaks):
            # Skip if slot overlaps with existing booking
            if not any(abs((current - booking).total_seconds()) < SlotConfig.DURATION_MINUTES * 60 
                      for booking in existing_bookings):
                slots.append(current)
        current += slot_delta + buffer_delta
    
    return slots

async def check_availability_and_suggest_slot(
    db: AsyncIOMotorDatabase,
    provider_id: str,
    requested_time: datetime,
    timezone: Optional[str] = None
) -> ToolMessage:
    """Check slot availability and suggest alternatives."""
    
    # Validate input date
    date = requested_time.date().isoformat()
    max_future_date = datetime.now() + timedelta(days=SlotConfig.MAX_DAYS_AHEAD)
    
    if requested_time.date() > max_future_date.date():
        return ToolMessage(
            name="check_availability",
            content=f"Bookings can only be made up to {SlotConfig.MAX_DAYS_AHEAD} days in advance.",
            parameters={}
        )

    # Get provider schedule
    schedule = await get_provider_schedule(db, provider_id, date)
    if not schedule:
        return ToolMessage(
            name="check_availability",
            content="Provider schedule not found. Please verify the provider ID.",
            parameters={}
        )

    # Check holiday
    if date in schedule.get("holidays", []):
        return ToolMessage(
            name="check_availability",
            content=f"The provider is not available on {date} (holiday).",
            parameters={}
        )

    # Get existing bookings
    existing_bookings = await db["bookings"].distinct(
        "timestamp",
        {
            "provider_id": provider_id,
            "timestamp": {
                "$gte": datetime.fromisoformat(f"{date}T00:00:00"),
                "$lt": datetime.fromisoformat(f"{date}T23:59:59")
            },
            "status": {"$in": ["PENDING", "CONFIRMED"]}
        }
    )

    # Generate available slots
    available_slots = await generate_available_slots(schedule, date, existing_bookings)
    
    if not available_slots:
        return ToolMessage(
            name="check_availability",
            content=f"No available slots on {date}. Would you like to check another date?",
            parameters={}
        )

    # Find matching or nearest slot
    requested_slot = min(available_slots, key=lambda x: abs((x - requested_time).total_seconds()))
    time_diff = abs((requested_slot - requested_time).total_seconds() / 60)

    if time_diff < 5:  # Within 5 minutes of requested time
        return ToolMessage(
            name="check_availability",
            content=f"Slot available at {requested_slot.strftime('%H:%M')}. Would you like to confirm?",
            parameters={}
        )
    else:
        next_slots = [slot.strftime('%H:%M') for slot in available_slots[:3]]
        return ToolMessage(
            name="check_availability",
            content=f"Requested time not available. Next available slots: {', '.join(next_slots)}. Would you like any of these?",
            parameters={}
        )