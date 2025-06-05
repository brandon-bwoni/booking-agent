from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def connect_db(cls, uri: str):
        cls.client = AsyncIOMotorClient(uri)
        cls.db = cls.client.wondabox
        # Verify connection
        await cls.client.admin.command('ismaster')
        print("Connected to MongoDB!")

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()
            print("MongoDB connection closed!")