from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from bson import ObjectId
from pydantic.json_schema import JsonSchemaValue

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, info):
        if not ObjectId.is_valid(value):
            raise ValueError(f"Invalid ObjectId: {value}")
        return ObjectId(value)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: JsonSchemaValue, handler) -> JsonSchemaValue:
        # Call the handler to ensure compatibility with Pydantic's schema logic
        json_schema = handler(schema)
        # Modify the schema to represent this as a string type
        json_schema.update(type="string")
        return json_schema

    @classmethod
    def __pydantic_modify_json_schema__(cls, schema: dict) -> None:
        schema.update(type="string")


class User(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    username: str
    password: str
    identityKey: str
    schnorKey: str
    schnorSig: str
    otpKeys: Optional[List[Dict[int, str]]]

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
           "example": {
                "_id": "507f191e810c19729de860ea",
                "username": "john_doe",
                "password": "Secure password",
                "identityKey": "identity key",
                "schnorKey": "Schnor Key",
                "schnorSig": "Schnor Sig",
                "otpKeys": [
                    {1: "DH Public Key 1"},
                    {2: "DH Public Key 2"}
                ]
            }
        }

class UserResponse(User):
    password: Optional[str] = Field(default=None, exclude=True)
    id: Optional[PyObjectId] = Field(alias="_id")
    identityKey: str
    schnorKey: str
    schnorSig: str
    username: str
    otpKeys: Optional[List[Dict[int, str]]]

    class Config:
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "_id": "507f191e810c19729de860ea",
                "username": "john_doe",
                "identityKey": "identity key",
                "schnorKey": "Schnor Key",
                "schnorSig": "Schnor Sig",
                "otpKeys": [
                    {1: "DH Public Key 1"},
                    {2: "DH Public Key 2"}
                ]
            }
        }

class UserRegister(BaseModel):
    username: str
    password: str
    identityKey: str
    schnorKey: str
    schnorSig: str

class UserLogin(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
