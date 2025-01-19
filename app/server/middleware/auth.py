from jose import jwt, JWTError
from fastapi import Request, HTTPException, status, Depends
from os import getenv

SECRET_KEY = getenv("JWT_SECRET")
ALGORITHM = getenv("JWT_ALGO") 

async def authenticate_user(request: Request):
    authorization: str = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to log in first.",
        )

    token = authorization.split("Bearer ")[-1] 
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload 
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )