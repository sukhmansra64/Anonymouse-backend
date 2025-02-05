from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional, List
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


class Chatroom(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    members: List[PyObjectId] = []
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "_id": "507f191e810c19729de860ea",
                "name": "General",
                "description": "A chatroom for general discussions",
                "members": ["507f191e810c19729de860ea", "507f191e810c19729de860eb"]
            }
        }

class SentChatroom(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    members: List[PyObjectId]


