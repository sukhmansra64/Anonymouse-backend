from fastapi import APIRouter, Depends, HTTPException, status, Response
from bson import ObjectId
from app.server.database import get_db
from app.server.models.message import Message, SentMessage, MessageDetails
from app.server.middleware.auth import authenticate_user
from typing import List

db = get_db()
router = APIRouter()

# @route GET api/message/test
# @description Test messages route
# @access Public
@router.get("/test")
async def test():
    return "Messages route working."


# @route GET api/message/chatroom_id
# @description Get messages from chatroom
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

    if str(user_id) not in map(str, chatroom.get("members", [])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this chatroom."
        )

    messages = await db["Messages"].find({"chatroom": ObjectId(chatroom_id)}).to_list(100)

    if not messages:
        return []

    for message in messages:
        message["_id"] = str(message["_id"])
        message["chatroom"] = str(message["chatroom"])
        message["sender"] = str(message["sender"])

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
    chatroom_id = message.chatroom

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

    message_dict = {
        "chatroom": ObjectId(chatroom_id),
        "sender": ObjectId(user_id),
        "message": {
            "content": message.message.content,
            "pubKey": message.message.pubKey,
            "privKeyId": message.message.privKeyId,
            "timestamp": message.message.timestamp
        }
    }

    result = await db["Messages"].insert_one(message_dict)
    message_dict["_id"] = str(result.inserted_id)

    response.status_code = status.HTTP_200_OK
    return Message(
        id=message_dict["_id"],
        chatroom=message_dict["chatroom"],
        sender=message_dict["sender"],
        message=MessageDetails(
            content=message_dict["message"]["content"],
            pubKey=message_dict["message"]["pubKey"],
            privKeyId=message_dict["message"]["privKeyId"],
            timestamp=message_dict["message"]["timestamp"]
        )
    )

#@route PUT api/message/read/
#@description Mark message as read
#@access Protected
@router.put("/read", response_model=dict)
async def mark_messages_as_read_and_delete(
    message_ids: List[str],
    response: Response,
    payload: dict = Depends(authenticate_user)
):
    user_id = payload["user_id"]

    try:
        object_ids = [ObjectId(msg_id) for msg_id in message_ids]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid message ID format.")

    messages = await db["Messages"].find({"_id": {"$in": object_ids}}).to_list(len(object_ids))
    
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No messages found!"
        )

    messages_to_delete = []
    
    for message in messages:
        chatroom = await db["Chatrooms"].find_one({"_id": message["chatroom"]})
        if not chatroom:
            continue

        chatroom_members = set(map(str, chatroom.get("members", [])))
        read_by_users = set(map(str, message.get("readBy", [])))

        if str(user_id) not in read_by_users:
            await db["Messages"].update_one(
                {"_id": message["_id"]},
                {"$addToSet": {"readBy": str(user_id)}}
            )
            read_by_users.add(str(user_id))

        if chatroom_members == read_by_users:
            messages_to_delete.append(message["_id"])

    if messages_to_delete:
        await db["Messages"].delete_many({"_id": {"$in": messages_to_delete}})

    response.status_code = status.HTTP_200_OK
    return {
        "message": "Messages read."
    }