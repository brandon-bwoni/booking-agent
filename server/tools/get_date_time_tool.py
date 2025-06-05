from datetime import datetime
import pytz
import dateparser
from typing import Union
from zoneinfo import available_timezones
from langchain_core.messages import ToolMessage

def parse_relative_datetime(
    user_phrase: str, 
    user_datetime: str, 
    user_timezone: str
) -> Union[str, ToolMessage]:
    """
    Parses a relative date expression like 'next week Tuesday' using the user's current datetime and timezone.

    Args:
        user_phrase: str - Natural language date (e.g., "next Friday at 2pm")
        user_datetime: str - ISO format datetime string from user's device
        user_timezone: str - IANA timezone name (e.g., "Africa/Harare")

    Returns:
        Union[str, ToolMessage]: Either ISO datetime string or ToolMessage for missing info
    """
    
    # Check for missing parameters
    missing_params = []
    if not user_phrase:
        missing_params.append("user_phrase")
    if not user_datetime:
        missing_params.append("user_datetime")
    if not user_timezone:
        missing_params.append("user_timezone")
    
    if missing_params:
        return ToolMessage(
            name="parse_relative_datetime",
            content=f"Please provide the following missing information: {', '.join(missing_params)}",
            parameters={
                param: {"type": "string", "description": get_param_description(param)}
                for param in missing_params
            }
        )
    
    # Validate timezone
    if user_timezone not in available_timezones():
        return ToolMessage(
            name="parse_relative_datetime",
            content=f"Invalid timezone: {user_timezone}. Please provide a valid IANA timezone name.",
            parameters={
                "user_timezone": {
                    "type": "string",
                    "description": "Valid IANA timezone name (e.g., 'Africa/Harare')"
                }
            }
        )

    # Validate datetime format
    if not is_valid_iso_datetime(user_datetime):
        return ToolMessage(
            name="parse_relative_datetime",
            content="Invalid datetime format. Please provide a valid ISO format datetime.",
            parameters={
                "user_datetime": {
                    "type": "string",
                    "description": "ISO format datetime string (e.g., '2025-06-04T10:00:00')"
                }
            }
        )

    # Parse the datetime
    reference_dt = datetime.fromisoformat(user_datetime)
    timezone = pytz.timezone(user_timezone)
    reference_dt = timezone.localize(reference_dt)

    # Configure parser settings
    parser_settings = {
        "RELATIVE_BASE": reference_dt,
        "TIMEZONE": user_timezone,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": 'future'
    }

    # Parse the relative datetime
    parsed_dt = dateparser.parse(user_phrase, settings=parser_settings)
    
    if parsed_dt is None:
        return ToolMessage(
            name="parse_relative_datetime",
            content=f"Could not understand the date/time phrase: '{user_phrase}'. Please rephrase.",
            parameters={
                "user_phrase": {
                    "type": "string",
                    "description": "Natural language date expression (e.g., 'next Friday at 2pm')"
                }
            }
        )

    return parsed_dt.isoformat()

def is_valid_iso_datetime(datetime_str: str) -> bool:
    """Validate if a string is a valid ISO format datetime"""
    try:
        datetime.fromisoformat(datetime_str)
        return True
    except ValueError:
        return False

def get_param_description(param: str) -> str:
    """Helper function to get parameter descriptions"""
    descriptions = {
        "user_phrase": "Natural language date expression (e.g., 'next Friday at 2pm')",
        "user_datetime": "ISO format datetime string (e.g., '2025-06-04T10:00:00')",
        "user_timezone": "IANA timezone name (e.g., 'Africa/Harare')"
    }
    return descriptions.get(param, "")