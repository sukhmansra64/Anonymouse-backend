from fastapi import APIRouter, Body, Response, status, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
from os import getenv
from jose import jwt
from datetime import datetime, timedelta


from app.server.database import get_db
from app.server.models.user import User, UserResponse, UserLogin
from app.server.middleware.auth import authenticate_user

db = get_db()

router = APIRouter()

SECRET_KEY = getenv("JWT_SECRET")
ALGORITHM = getenv("JWT_ALGO")

#@route GET api/user/test
#@description Test user route
#@access Public
@router.get("/test")
async def read_users():
    return {"message": "Users endpoint"}


# @route GET /api/user/test-login
# @description Test if the user is logged in by validating the JWT token
# @access Private
@router.get("/test-login")
async def test_login(response: Response, payload: dict = Depends(authenticate_user)):
    response.status_code = status.HTTP_200_OK
    return {
        "message": "Login successful!",
        "user_id": payload.get("user_id"),
        "issued_at": payload.get("iat"),
        "expires_at": payload.get("exp"),
    }

#@route POST api/user
#@description Create a user
#@access Public
@router.post("/", response_model=UserResponse)
async def create_user(user: User, response: Response):
    user_dict = user.dict(by_alias=True)
    username = user_dict["username"]
    arr = await db["Users"].find({"username":username}).to_list()
    if len(arr) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists!")
    result = await db["Users"].insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    response.status_code = status.HTTP_200_OK
    
    return user_dict

# @route POST /api/user/login
# @description Logs user in and returns JWT
# @access Public
@router.post("/login")
async def login(user_login: UserLogin, response: Response):

    user = await db["Users"].find_one({"username": user_login.username, "password": user_login.password})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or Password is incorrect."
        )
    
    expiration = datetime.utcnow() + timedelta(minutes=15)
    payload = {
        "user_id": str(user["_id"]),
        "exp": expiration,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    response.status_code = status.HTTP_200_OK
    return {
        "message": f"{user['profile']['name']} has been logged in successfully.",
        "token": token,
    }

# @route GET api/user
# @description Get all users
# @access Protected
@router.get("/", response_model=list[User])
async def get_all_users(
    response: Response,
    payload: dict = Depends(authenticate_user)
):
    users = await db["Users"].find().to_list()
    response.status_code = status.HTTP_200_OK
    return users

# @route GET api/user/{user_id}
# @description Get User by ID
# @access Protected
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    user = await db["Users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!"
        )
    response.status_code = status.HTTP_200_OK
    return user

# @route PUT api/user/{user_id}
# @description Update a user by ID
# @access Protected
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, 
    user: dict, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    if payload["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this user."
        )
    
    update_result = await db["Users"].update_one(
        {"_id": ObjectId(user_id)}, {"$set": jsonable_encoder(user)}
    )
    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!"
        )
    updated_user = await db["Users"].find_one({"_id": ObjectId(user_id)})
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found after update!"
        )
    response.status_code = status.HTTP_200_OK
    return updated_user

# @route DELETE api/user/{user_id}
# @description Delete a user by ID
# @access Protected
@router.delete("/{user_id}", response_model=str)
async def delete_user(
    user_id: str, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    if payload["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this user."
        )
    
    delete_result = await db["Users"].delete_one({"_id": ObjectId(user_id)})
    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!"
        )
    
    response.status_code = status.HTTP_200_OK
    return "User deleted."


