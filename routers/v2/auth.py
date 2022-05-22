from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from models.user import User
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from jose import jwt

import hashlib
import datetime
from config import secret

from fastapi import status
from utils.jwt import generate_login_jwt

import asyncio
auth_route = APIRouter(
    prefix="/auth",
    tags=["auth | 登录"],
)


login_invalid = HTTPException(401, 'username or password invalid')
@auth_route.post('/login')
async def login_auth(req: Request, response: Response, f: OAuth2PasswordRequestForm = Depends(), expires:float=86400):
    """用户登录，令牌写在cookie里"""
    if not (u := (await User.atrychk(f.username))):
        raise login_invalid
    if not u.pw_chk(f.password):
        raise login_invalid
    u.last_access = datetime.datetime.now()
    u.last_ip = req.client.host
    await u.asave()

    token = generate_login_jwt(u, expires)
    response.set_cookie("Authorization", token, expires, samesite='None', secure=True)
    return {"jwt": token} # TODO: [insecure] remove return jwt directly


@auth_route.post('/register')
async def register_auth(req:Request, response: Response, f: OAuth2PasswordRequestForm = Depends()):
    """用户注册，令牌写在cookie里"""
    expires = 86400
    if not f.username or not f.password:
        raise HTTPException(400, 'handle or password cannot be empty')
    if (await User.atrychk(f.username)):
        raise HTTPException(400, 'user handle already exists')
    u = User(pk=f.username)
    u.pw_set(f.password)
    u.last_access = datetime.datetime.now()
    u.last_ip = req.client.host
    await u.asave_report_error()
    token = generate_login_jwt(u, expires)
    response.set_cookie("Authorization", token, expires, samesite='None', secure=True)
    return {"jwt": token} # TODO: [insecure] remove return jwt directly


@auth_route.put('/password')
async def change_password(req:Request, response: Response, username: str=Form(), password: str=Form(), new: str=Form()):
    expires = 86400
    if not username or not password or not new:
        raise HTTPException(400, 'handle or password cannot be empty')
    if password == new:
        raise HTTPException(400, 'password not changed')
    if not (u := await User.atrychk(username)):
        raise login_invalid
    if not u.pw_chk(password):
        raise login_invalid
    u.pw_set(password)
    u.jwt_updated = datetime.datetime.now()
    u.last_access = datetime.datetime.now()
    u.last_ip = req.client.host
    await u.asave()
    token = generate_login_jwt(u, expires)
    response.set_cookie("Authorization", token, expires, samesite='None', secure=True)
    return {"jwt": token} # TODO: [insecure] remove return jwt directly

