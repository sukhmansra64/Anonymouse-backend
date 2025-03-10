from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.server.database import get_db


db = get_db()

async def generate_chatroom_name(member_ids, current_user_id):
    other_members_ids = [ObjectId(member) for member in member_ids if str(member) != str(current_user_id)]
    other_members = await db["Users"].find(
        {"_id": {"$in": other_members_ids}}
    ).to_list(None)

    chatroom_name = ", ".join([user.get("username", "Unknown") for user in other_members])

    print(chatroom_name)

    return chatroom_name if chatroom_name else "Unnamed Chatroom"

