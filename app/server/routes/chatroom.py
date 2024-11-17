from fastapi import APIRouter, Depends, HTTPException, status, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.server.database import get_db
from app.server.models.chatroom import Chatroom

db = get_db()
router = APIRouter()

# @route GET api/chatroom/test
# @description Test chatroom route
# @access Public
@router.get("/test")
async def test():
    return "Chatroom route works."

# @route GET api/chatroom
# @description Get all chatrooms
# @access Public
@router.get("/", response_model=list[Chatroom])
async def get_all_chatrooms(response: Response):
    chatrooms = await db["Chatrooms"].find().to_list()
    response.status_code = status.HTTP_200_OK
    return chatrooms

# @route GET api/chatroom/{chatroom_id}
# @description Get a chatroom by ID
# @access Public
@router.get("/{chatroom_id}", response_model=Chatroom)
async def get_chatroom(chatroom_id: str, response: Response):
    chatroom = await db["Chatrooms"].find_one({"_id": ObjectId(chatroom_id)})
    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chatroom not found!"
        )
    response.status_code = status.HTTP_200_OK
    return chatroom

# @route POST api/chatroom
# @description Create a new chatroom
# @access Public
@router.post("/", response_model=Chatroom)
async def create_chatroom(chatroom: Chatroom, response: Response):
    chatroom_dict = chatroom.dict(by_alias=True)
    result = await db["Chatrooms"].insert_one(chatroom_dict)
    chatroom_dict["_id"] = str(result.inserted_id)
    response.status_code = status.HTTP_200_OK
    return chatroom_dict

# @route DELETE api/chatroom/{chatroom_id}
# @description Delete a chatroom by ID
# @access Public
@router.delete("/{chatroom_id}", response_model=str)
async def delete_chatroom(chatroom_id: str, response: Response):
    delete_result = await db["Chatrooms"].delete_one({"_id": ObjectId(chatroom_id)})
    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom not found!"
        )
    response.status_code = status.HTTP_200_OK
    return "Chatroom Deleted!"

# @route POST api/chatroom/{chatroom_id}/join
# @description Add a user to the chatroom members list
# @access Public
@router.post("/{chatroom_id}/join", response_model=str)
async def join_chatroom(chatroom_id: str, user:dict, response: Response):
    user_id = user["user_id"]
    chatroom = await db["Chatrooms"].find_one({"_id": ObjectId(chatroom_id)})
    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom not found!"
        )
    if ObjectId(user_id) in chatroom.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already a member of the chatroom!"
        )
    update_result = await db["Chatrooms"].update_one(
        {"_id": ObjectId(chatroom_id)},
        {"$addToSet": {"members": ObjectId(user_id)}}  # Avoid duplicate additions
    )
    if update_result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add user to chatroom!"
        )
    response.status_code = status.HTTP_200_OK
    return f"User {user_id} successfully added to chatroom {chatroom_id}!"
