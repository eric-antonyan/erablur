from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import MONGO_URI

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.get_default_database()
heroes_collection = db["heroes"]
history_collection = db["history"]
users_collection = db["users"]
channels_collection = db["connected_channels"]
