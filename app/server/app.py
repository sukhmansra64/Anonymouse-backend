from fastapi import FastAPI, Depends
from dotenv import load_dotenv
from fastapi_socketio import SocketManager
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from os import getenv
from jose import jwt, JWTError

from app.server.routes.user import router as UserRouter
from app.server.routes.chatroom import router as ChatroomRouter
from app.server.routes.message import router as MessageRouter

from app.server.database import get_db

from app.server.models.chatroom import Chatroom
from app.server.models.message import Message, MessageDetails

load_dotenv()

SECRET_KEY = getenv("JWT_SECRET")
ALGORITHM = getenv("JWT_ALGO")

app = FastAPI()
socket_manager = SocketManager(app=app, mount_location="/socket.io", cors_allowed_origins=["http://localhost:3000"], allow_credentials=True)
db = get_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(UserRouter, tags=["User"],prefix="/api/user")
app.include_router(ChatroomRouter, tags=["Chatroom"], prefix="/api/chatroom")
app.include_router(MessageRouter,tags=["Message"], prefix="/api/message")

@app.get("/", tags=["Root"])
async def root():
    return {"Message": "Server is working"}

@app.get("/test-db")
async def test_db(database=Depends(get_db)):
    collections = await database.list_collection_names()
    return {"collections": collections}

#Socket.IO Events
@socket_manager.on("connect")
async def connect(sid, environ):
    cookies = environ.get("HTTP_COOKIE", "")
    print(cookies)
    cookie_dict = {cookie.split("=")[0]: cookie.split("=")[1] for cookie in cookies.split("; ") if "=" in cookie}

    token = cookie_dict.get("Authorization")
    if not token:
        await socket_manager.disconnect(sid)
        return
    if not token or len(token.split(".")) != 3:
            raise JWTError("Invalid token format")
            
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise ConnectionRefusedError("Invalid token payload")
        await socket_manager.save_session(sid, {"user_id": user_id})
        print(f"User {user_id} connected via socket: {sid}")
    except (JWTError, ConnectionRefusedError) as e:
        print(f"Connection refused: {e}")
        raise e

@socket_manager.on("disconnect")
async def disconnect(sid):
    print(f"Socket disconnected: {sid}")

@socket_manager.on("joinRoom")
async def join_room(sid, data):
    session = await socket_manager.get_session(sid)
    user_id = session.get("user_id")
    chatroom_id = data.get("chatroomId")
    if not chatroom_id:
        return await socket_manager.emit(
            "error", {"message": "chatroomId is required"}, room=sid
        )
    chatroom = await db["Chatrooms"].find_one({"_id": ObjectId(chatroom_id)})
    if not chatroom:
        return await socket_manager.emit(
            "error", {"message": "Chatroom not found"}, room=sid
        )
    if ObjectId(user_id) not in chatroom.get("members", []):
        return await socket_manager.emit(
            "error", {"message": "User not authorized to join this chatroom"}, room=sid
        )
    await socket_manager.enter_room(sid, chatroom_id)
    print(f"User {user_id} joined chatroom {chatroom_id}")
    await socket_manager.emit(
        "notification",
        {"message": f"User {user_id} joined the chatroom"},
        room=chatroom_id,
    )


@socket_manager.on("leaveRoom")
async def leave_room(sid, data):
    chatroom_id = data.get("chatroomId")
    await socket_manager.leave_room(sid, chatroom_id)
    print(f"Socket {sid} left chatroom: {chatroom_id}")
    await socket_manager.emit(
        "notification",
        {"message": f"User left chatroom {chatroom_id}"},
        room=chatroom_id,
    )


@socket_manager.on("chatroomMessage")
async def chatroom_message(sid, data):
    session = await socket_manager.get_session(sid)
    user_id = session.get("user_id")
    chatroom_id = data.get("chatroomId")
    message_details = data.get("message")
    if not chatroom_id:
        return await socket_manager.emit(
            "error", {"message": "chatroomId is required"}, room=sid
        )
    if not message_details:
        return await socket_manager.emit(
            "error", {"message": "Message details are required"}, room=sid
        )
    if not message_details.get("content") or message_details["content"].strip() == "":
        return await socket_manager.emit(
            "error", {"message": "Message content cannot be empty"}, room=sid
        )
    if not message_details.get("pubKey") or not message_details.get("timestamp"):
        return await socket_manager.emit(
            "error", {"message": "pubKey and timestamp are required"}, room=sid
        )
    if not message_details.get("privKeyId") or not message_details.get("timestamp"):
        return await socket_manager.emit(
            "error", {"message": "pubKey and timestamp are required"}, room=sid
        )
    chatroom = await db["Chatrooms"].find_one({"_id": ObjectId(chatroom_id)})
    if not chatroom:
        return await socket_manager.emit(
            "error", {"message": "Chatroom not found"}, room=sid
        )
    if ObjectId(user_id) not in chatroom.get("members", []):
        return await socket_manager.emit(
            "error", {"message": "User is not a member of this chatroom"}, room=sid
        )
    message = Message(
        chatroom=chatroom_id,
        sender=user_id,
        message=MessageDetails(
            content=message_details["content"],
            pubKey=message_details["pubKey"],
            privKeyId=message_details["privKeyId"],
            timestamp=message_details["timestamp"]
        )
    )
    result = await db["Messages"].insert_one(message.dict(by_alias=True))
    saved_message = message.dict(by_alias=True)
    saved_message["_id"] = str(result.inserted_id)

    print(f"Message saved in chatroom {chatroom_id}: {message_details['content']}")
    await socket_manager.emit(
        "newMessage",
        {
            "_id": saved_message["_id"],
            "chatroom": chatroom_id,
            "sender": user_id,
            "message": {
                "content": message_details["content"],
                "pubKey": message_details["pubKey"],
                "privKeyId": message_details["privKeyId"],
                "timestamp": message_details["timestamp"]
            }
        },
        room=chatroom_id,
    )