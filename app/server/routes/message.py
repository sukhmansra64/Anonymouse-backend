from fastapi import APIRouter, Depends, HTTPException, status, Response
from bson import ObjectId
from app.server.database import get_db
from app.server.models.message import Message, SentMessage
from app.server.middleware.auth import authenticate_user

db = get_db()
router = APIRouter()

# @route GET api/message/test
# @description Test messages route
# @access Public
@router.get("/test")
async def test():
    return "Messages route working."

# @route GET api/message/{chatroom_id}
# @description Get all messages in a chatroom
# @access Protected
@router.get("/{chatroom_id}", response_model=list[Message])
async def get_messages(
    chatroom_id: str, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    user_id = payload["user_id"]

    chatroom = await db["Chatrooms"].find_one({"_id": ObjectId(chatroom_id)})
    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom not found!"
        )

    if ObjectId(user_id) not in chatroom.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this chatroom."
        )

    messages = await db["Messages"].find({"chatroom_id": ObjectId(chatroom_id)}).to_list(100)
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No messages found in this chatroom!"
        )

    response.status_code = status.HTTP_200_OK
    return messages

# @route POST api/message
# @description Send a message to a chatroom
# @access Protected
@router.post("/", response_model=Message)
async def send_message(
    message: SentMessage, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    user_id = payload["user_id"]
    chatroom_id = message.chatroom_id

    chatroom = await db["Chatrooms"].find_one({"_id": ObjectId(chatroom_id)})
    if not chatroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom not found!"
        )

    if ObjectId(user_id) not in chatroom.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to send messages in this chatroom."
        )

    message_dict = message.dict(by_alias=True)
    message_dict["sender"] = user_id

    result = await db["Messages"].insert_one(message_dict)
    message_dict["_id"] = str(result.inserted_id)
    response.status_code = status.HTTP_200_OK
    return message_dict