from fastapi import APIRouter, Body, Response, status, HTTPException
from fastapi.encoders import jsonable_encoder
from bson import ObjectId

from app.server.database import get_db
from app.server.models.user import User, UserResponse

db = get_db()

router = APIRouter()

#@route GET api/user/test
#@description Test user route
#@access Public
@router.get("/test")
async def read_users():
    return {"message": "Users endpoint"}

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

#@route GET api/user
#@description Get all users
#@access Public
@router.get("/", response_model=list[User])
async def get_all_users(response: Response):
    users = await db["Users"].find().to_list()
    response.status_code = status.HTTP_200_OK
    return users

#@route GET api/user/{user_id}
#@description Get User by ID
#@access Public
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, response: Response):
    user = await db["Users"].find_one({"_id":ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!"
        )
    response.status_code = status.HTTP_200_OK
    return user

# @route PUT api/user/{user_id}
# @description Update a user by ID
# @access Public
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user: dict, response: Response):
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
# @access Public
@router.delete("/{user_id}", response_model=str)
async def delete_user(user_id: str, response: Response):
    delete_result = await db["Users"].delete_one({"_id": ObjectId(user_id)})
    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!"
        )
    response.status_code = status.HTTP_200_OK
    return "User deleted."


