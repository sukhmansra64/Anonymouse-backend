from fastapi import APIRouter, Depends, HTTPException, status, Response
from bson import ObjectId
from app.server.database import get_db
from app.server.models.message import Message

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
# @access Public
@router.get("/{chatroom_id}", response_model=list[Message])
async def get_messages(chatroom_id: str, response: Response):
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
# @access Public
@router.post("/", response_model=Message)
async def send_message(message: Message, response: Response):
    message_dict = message.dict(by_alias=True)
    if not await db["Chatrooms"].find_one({"_id": ObjectId(message.chatroom_id)}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatroom not found!"
        )
    result = await db["Messages"].insert_one(message_dict)
    message_dict["_id"] = str(result.inserted_id)
    response.status_code = status.HTTP_201_CREATED
    return message_dict