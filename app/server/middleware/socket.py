from fastapi_socketio import SocketManager
from fastapi import FastAPI

app = FastAPI()
socket_manager = SocketManager(app=app, mount_location="/socket.io", cors_allowed_origins=[])