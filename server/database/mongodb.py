import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

class DBConnect:
    _instance = None
    _client = None
    _db = None

    @classmethod
    async def get_instance(cls):
        """Get singleton instance of database connection"""
        if not cls._instance:
            cls._instance = DBConnect()
            await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """Initialize database connection"""
        uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client["wondabox"]
        # Verify connection
        await self._client.admin.command('ping')

    @property
    def db(self):
        """Get database instance"""
        if not self._db:
            raise RuntimeError("Database not initialized. Call get_instance() first")
        return self._db

    async def close(self):
        """Close database connection"""
        if self._client:
            self._client.close()
            self._instance = None