import os
import asyncio
from pymongo import AsyncMongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')

async def initiate_db():
    """Initialize MongoDB connection and create time series collection"""
    try:
        client =  AsyncMongoClient(uri)
        db = client["wondabox"]
        await db.create_collection(
            "bookings", 
            timeseries={"timeField": "timestamp"}
        )
        print("Database and collection created successfully!")
        return db
    except Exception as err:
        print(f"Error creating database: {err}")
        return None
    finally:
       await client.close()

if __name__ == "__main__":
    asyncio.run(initiate_db())