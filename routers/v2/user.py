import copy
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from models.user import User
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from jose import jwt

import hashlib
import datetime
from config import secret

from fastapi import status
from utils.jwt import generate_login_jwt, should_login
from utils.ctx import g

import asyncio
user_route = APIRouter(
    prefix="/user",
    tags=["user | 用户"],
)

@user_route.get('/{user_id}')
async def get_user(user_id: str):
    """获取指定用户的信息"""
    u = await User.atrychk(user_id, projection={
        '_id': 1,
        'avatar': 1,
        'nick': 1,
        'desc': 1,
        'last_access': 1,
        # 'authority_level': 1, # 你们觉得有没有必要
        'rating': 1,
        'solved': 1,
        'tried': 1,
    })
    if not u: raise HTTPException(404, 'no such user')
    return u.to_mongo()
