from fastapi import APIRouter, Depends, HTTPException, status, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.server.database import get_db
from app.server.models.chatroom import Chatroom, SentChatroom
from app.server.middleware.auth import authenticate_user
from app.server.middleware.socket import socket_manager

db = get_db()
router = APIRouter()

#@route GET api/chatroom/test
#@description Test chatroom route
#@access Public
@router.get("/test")
async def test():
    return "Chatroom route works."

#@route GET api/chatroom
#@description Get all chatrooms the user is in
#@access Protected
@router.get("/", response_model=list[dict])
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

    chatrooms = await db["Chatrooms"].find({"members": ObjectId(user_id)}).to_list(None)

    formatted_chatrooms = []
    for chatroom in chatrooms:
        formatted_chatrooms.append({
            "_id": str(chatroom["_id"]),
            "name": await generate_chatroom_name(chatroom["members"], user_id),
            "members": [str(member) for member in chatroom["members"]]
        })

    response.status_code = status.HTTP_200_OK
    return formatted_chatrooms


#@route GET api/chatroom/{chatroom_id}
#@description Get a chatroom by ID
#@access Protected
@router.get("/{chatroom_id}", response_model=dict)
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
    return {
        "_id": str(chatroom["_id"]),
        "name": await generate_chatroom_name(chatroom["members"], user_id),
        "members": [str(member) for member in chatroom["members"]]
    }


#@route POST api/chatroom
#@description Create a new chatroom
#@access Protected
@router.post("/", response_model=dict)
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
    chatroom_dict["members"] = sorted(
        [ObjectId(user_id)] + [ObjectId(m) for m in chatroom_dict.get("members", [])]
    )

    existing_chatroom = await db["Chatrooms"].find_one({"members": chatroom_dict["members"]})

    if existing_chatroom:
        response.status_code = status.HTTP_200_OK
        return {
            "_id": str(existing_chatroom["_id"]),
            "name": await generate_chatroom_name(existing_chatroom["members"], user_id),
            "members": [str(member) for member in existing_chatroom["members"]]
        }

    result = await db["Chatrooms"].insert_one(chatroom_dict)
    chatroom_dict["_id"] = str(result.inserted_id)

    chatroom_dict["name"] = await generate_chatroom_name(chatroom_dict["members"], user_id)
    chatroom_dict["members"] = [str(member) for member in chatroom_dict["members"]]

    for member in chatroom_dict["members"]:
        member_chatroom_name = await generate_chatroom_name(chatroom_dict["members"], member)
        print(f"Chatroom Name for Member {member}: {member_chatroom_name}")
        chatroom_data = {
            "_id": chatroom_dict["_id"],
            "name": member_chatroom_name,
            "members": chatroom_dict["members"]
        }
        if member != user_id:
            await socket_manager.emit("newChatroom", chatroom_data, room=member)

    response.status_code = status.HTTP_201_CREATED
    return chatroom_dict




#@route POST api/chatroom/{chatroom_id}/join
#@description Add the authenticated user to the chatroom members list
#@access Protected
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

#@route DELETE api/chatroom/{chatroom_id}
#@description Delete a chatroom and it's messages
#@access Protected
@router.delete("/{chatroom_id}", response_model=str)
async def delete_chatroom(
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
            detail="Chatroom not found."
        )

    if ObjectId(user_id) not in chatroom["members"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this chatroom."
        )

    await db["Messages"].delete_many({"chatroom": ObjectId(chatroom_id)})

    delete_result = await db["Chatrooms"].delete_one({"_id": ObjectId(chatroom_id)})

    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chatroom."
        )
    
    await socket_manager.emit(
        "chatroomDeleted",
        {"message": f"{chatroom_id}"},
        room=chatroom_id
    )


    response.status_code = status.HTTP_200_OK
    return f"Chatroom {chatroom_id} successfully deleted."


async def generate_chatroom_name(member_ids, current_user_id):
    print(f"🔹 Members before filtering: {member_ids}")
    print(f"🔹 Current user ID: {current_user_id}")

    # Convert members to ObjectId, except the current user
    other_members_ids = [ObjectId(member) for member in member_ids if str(member) != str(current_user_id)]
    
    print(f"🔹 Members after filtering: {other_members_ids}")  # Debugging print

    other_members = await db["Users"].find(
        {"_id": {"$in": other_members_ids}}
    ).to_list(None)

    print(f"🔹 Fetched Members: {other_members}")  # Debugging print

    chatroom_name = ", ".join([user.get("username", "Unknown") for user in other_members])

    print(f"✅ Generated Chatroom Name: {chatroom_name}")  # Debugging print

    return chatroom_name if chatroom_name else "Unnamed Chatroom"

