from fastapi import APIRouter, Depends, HTTPException, status, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.server.database import get_db
from app.server.models.chatroom import Chatroom, SentChatroom
from app.server.middleware.auth import authenticate_user

db = get_db()
router = APIRouter()

# @route GET api/chatroom/test
# @description Test chatroom route
# @access Public
@router.get("/test")
async def test():
    return "Chatroom route works."

# @route GET api/chatroom
# @description Get all chatrooms the user is in
# @access Protected
@router.get("/", response_model=list[Chatroom])
async def get_user_chatrooms(
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )

    chatrooms = await db["Chatrooms"].find({"members": ObjectId(user_id)}).to_list()

    response.status_code = status.HTTP_200_OK
    return chatrooms


# @route GET api/chatroom/{chatroom_id}
# @description Get a chatroom by ID
# @access Protected
@router.get("/{chatroom_id}", response_model=Chatroom)
async def get_user_chatroom(
    chatroom_id: str, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )

    chatroom = await db["Chatrooms"].find_one(
        {"_id": ObjectId(chatroom_id), "members": ObjectId(user_id)}
    )

    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom not found or user is not a member."
        )

    response.status_code = status.HTTP_200_OK
    return chatroom


#@route POST api/chatroom
#@description Create a new chatroom
#@access Protected
@router.post("/", response_model=Chatroom)
async def create_chatroom(
    chatroom: SentChatroom, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )

    chatroom_dict = chatroom.dict(by_alias=True)
    chatroom_dict["members"] = sorted([ObjectId(user_id)] + [ObjectId(m) for m in chatroom_dict.get("members", [])])

    existing_chatroom = await db["Chatrooms"].find_one({"members": chatroom_dict["members"]})

    if existing_chatroom:
        response.status_code = status.HTTP_200_OK
        return existing_chatroom

    result = await db["Chatrooms"].insert_one(chatroom_dict)
    chatroom_dict["_id"] = str(result.inserted_id)

    response.status_code = status.HTTP_201_CREATED
    return chatroom_dict




# @route POST api/chatroom/{chatroom_id}/join
# @description Add the authenticated user to the chatroom members list
# @access Protected
@router.post("/{chatroom_id}/join", response_model=str)
async def join_chatroom(
    chatroom_id: str, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    user_id = payload.get("user_id") 

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )

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
        {"$addToSet": {"members": ObjectId(user_id)}}
    )

    if update_result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add user to chatroom!"
        )

    response.status_code = status.HTTP_200_OK
    return f"User {user_id} successfully added to chatroom {chatroom_id}!"

