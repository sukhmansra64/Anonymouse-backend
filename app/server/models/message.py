from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
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
        json_schema = handler(schema)
        json_schema.update(type="string")
        return json_schema

    @classmethod
    def __pydantic_modify_json_schema__(cls, schema: dict) -> None:
        schema.update(type="string")


class MessageDetails(BaseModel):
    content: str
    pubKey: str
    privKeyId: str
    timestamp: str
    readBy: list[str] = []


class Message(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    chatroom: PyObjectId
    sender: PyObjectId
    message: MessageDetails
    read_by: list[str] = []

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "id": "507f191e810c19729de860ea",
                "chatroom": "507f191e810c19729de860eb",
                "sender": "507f191e810c19729de860ec",
                "message": {
                    "content": "Hello, everyone!",
                    "pubKey": "public_key_example",
                    "privKeyId": "private_key_example",
                    "timestamp": "2024-12-02T12:00:00"
                }
            }
        }

class SentMessage(BaseModel):
    chatroom: PyObjectId
    message: MessageDetails