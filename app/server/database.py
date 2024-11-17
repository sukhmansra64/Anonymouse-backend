from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from os import getenv

load_dotenv()

URI = getenv("DB_URI")
client = AsyncIOMotorClient(URI) if URI else None

def get_db():
    if not client:
        raise ValueError("MongoDB client is not initialized. Check your DB_URI environment variable.")
    return client["Anonymouse"]






