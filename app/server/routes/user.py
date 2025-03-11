from fastapi import APIRouter, Body, Response, status, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
from os import getenv
from jose import jwt
from datetime import datetime, timedelta


from app.server.database import get_db
from app.server.models.user import User, UserResponse, UserLogin, UserRegister, ChangePasswordRequest
from app.server.middleware.auth import authenticate_user
from app.server.middleware.hash import hash_password, verify_password

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
async def create_user(new_user: UserRegister, response: Response):
    username = new_user.username
    password = new_user.password

    existing_user = await db["Users"].find_one({"username": username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists!"
        )
    
    hash = hash_password(password)

    user_dict = {
        "username": username,
        "password": hash["hashed_password"],
        "salt": hash["salt"],
        "identityKey": new_user.identityKey,
        "schnorrKey": new_user.schnorrKey,
        "schnorrSig": new_user.schnorrSig,
        "otpKeys": []
    }

    result = await db["Users"].insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)

    response.status_code = status.HTTP_200_OK
    return user_dict

# @route POST /api/user/login
# @description Logs user in and returns JWT
# @access Public
@router.post("/login")
async def login(user_login: UserLogin, response: Response):

    user = await db["Users"].find_one({"username": user_login.username})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or Password is incorrect."
        )
    
    if not verify_password(user_login.password, user["salt"], user["password"]):
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
        "message": f"User has been logged in successfully.",
        "token": token,
        "otpKeys": len(user["otpKeys"])
    }

# @route GET api/user
# @description Get all users
# @access Protected
@router.get("/", response_model=list[UserResponse])
async def get_all_users(
    response: Response,
    payload: dict = Depends(authenticate_user)
):
    users = await db["Users"].find().to_list()

    for user in users:
        if "otpKeys" in user and isinstance(user["otpKeys"], list):
            user["otpKeys"] = [
                {int(k): str(v)} for key in user["otpKeys"] for k, v in key.items()
                if isinstance(k, int) and isinstance(v, str) 
            ]

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
    
    if "otpKeys" in user and isinstance(user["otpKeys"], list):
            user["otpKeys"] = [
                {int(k): str(v)} for key in user["otpKeys"] for k, v in key.items()
                if isinstance(k, int) and isinstance(v, str) 
            ]
    
    response.status_code = status.HTTP_200_OK
    return user

#@route GET api/user/name/{userName}
#@description Get Users by Username
#@access Protected
@router.get("/name/{userName}", response_model=list[UserResponse])
async def getUserByName(userName: str, response: Response, payload:dict = Depends(authenticate_user)):
    user_id = payload["user_id"]
    users = await db["Users"].find(
        {
            "username": {"$regex": f"^{userName}", "$options": "i"},
            "_id": {"$ne": ObjectId(user_id)}  # Exclude the current user
        }
    ).to_list(10)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Username not found!"
        )
    for user in users:
        if "otpKeys" in user and isinstance(user["otpKeys"], list):
            user["otpKeys"] = [
                {int(k): str(v)} for key in user["otpKeys"] for k, v in key.items()
                if isinstance(k, int) and isinstance(v, str) 
            ]
    response.status_code = status.HTTP_200_OK
    return users



# @route PUT api/user
# @description Update the authenticated user's information
# @access Protected
@router.put("/", response_model=UserResponse)
async def update_user(
    user: dict, 
    response: Response, 
    payload: dict = Depends(authenticate_user)
):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
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
    
    if "otpKeys" in updated_user and isinstance(updated_user["otpKeys"], list):
            updated_user["otpKeys"] = [
                {int(k): str(v)} for key in updated_user["otpKeys"] for k, v in key.items()
                if isinstance(k, int) and isinstance(v, str) 
            ]
    
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

# @route PUT api/user/otpKeys
# @description Overwrites the authenticated user's otpKeys array with a new array
# @access Private
@router.put("/otpKeys", response_model=str)
async def update_otp_keys(otpKeys: list[dict], response: Response, payload: dict = Depends(authenticate_user)):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user = await db["Users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!",
        )

    if not isinstance(otpKeys, list) or any(not isinstance(key, dict) for key in otpKeys):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format for OTP keys. Expected an array of objects.",
        )

    await db["Users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"optKeys": otpKeys}}
    )

    response.status_code = status.HTTP_200_OK
    return "OTP keys updated successfully."

# @route DELETE api/user/otpKeys/{username}
# @description Pop a OTP key pair by username
# @access Protected
@router.delete("/otpKeys/{user_id}", response_model=dict)
async def pop_otp_key(
    user_id: str,
    response: Response,
    payload: dict = Depends(authenticate_user)
):
    target_user = await db["Users"].find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found!"
        )

    authenticated_user = await db["Users"].find_one({"_id": ObjectId(payload["user_id"])})
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found!"
        )

    otpKeys = target_user.get("otpKeys", [])
    if not otpKeys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OTP keys available for this user."
        )

    popped_key = otpKeys.pop(0)

    await db["Users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"otpKeys": otpKeys}}
    )

    response.status_code = status.HTTP_200_OK
    return {"popped_key": popped_key}

#@route POST api/user/change-password
#@description Change user password
#@access Protected
@router.post("/change-password", response_model=str)
async def change_password(
    request: ChangePasswordRequest,
    response: Response,
    payload: dict = Depends(authenticate_user)
):
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )

    current_password = request.currentPassword
    new_password = request.newPassword

    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both current and new passwords are required."
        )

    user = await db["Users"].find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!"
        )

    if not verify_password(current_password, user["salt"], user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect."
        )
    
    new_hashed_password = hash_password(new_password)

    await db["Users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "password": new_hashed_password["hashed_password"],
            "salt": new_hashed_password["salt"]
        }}
    )

    response.status_code = status.HTTP_200_OK
    return "Password changed."



