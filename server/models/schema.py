from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class BookingStatus(str):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class BookingBase(BaseModel):
    user_id: str 
    provider_id: str 
    service_type: str  
    description: Optional[str] 
    start_time: datetime 
    end_time: datetime  
    status: Literal[
        "pending", "confirmed", "cancelled", "rescheduled", "completed"
    ] = Field(default="pending")
    created_at: datetime 
    updated_at: datetime 


class BookingCreate(BaseModel):
    user_id: str
    provider_id: str
    service_type: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime


class BookingUpdate(BaseModel):
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: Optional[str]
    cancel_reason: Optional[str]


class BookingInDB(BookingBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
