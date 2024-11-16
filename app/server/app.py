from fastapi import FastAPI, Depends
from dotenv import load_dotenv

from app.server.routes.user import router as UserRouter
from app.server.database import get_db

load_dotenv()

app = FastAPI()

app.include_router(UserRouter, tags=["User"],prefix="/api/user")

@app.get("/", tags=["Root"])
async def root():
    return {"Message": "Server is working"}

@app.get("/test-db")
async def test_db(database=Depends(get_db)):
    collections = await database.list_collection_names()
    return {"collections": collections}