from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from models.user import User
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from jose import jwt

import hashlib
import datetime
from config import secret

import asyncio
auth_route = APIRouter(
    prefix="/auth",
    tags=["auth | 登录"],
)


class login_form(BaseModel):
    username: str
    password: str



def generate_login_jwt(user: User, expires: float=86400,):
    return jwt.encode(
        {
            'user': str(user.pk),
            'ts': str((datetime.datetime.now()+ datetime.timedelta(seconds=expires)).timestamp())
        },  # payload, 有效载体
        secret.jwt_key,  # 进行加密签名的密钥
    )


login_invalid = HTTPException(401, 'username or password invalid')
@auth_route.post('/login')
async def login_auth(response: Response, f: OAuth2PasswordRequestForm = Depends(), expires:float=86400):
    """用户登录，令牌写在cookie里"""
    if not (u := User.objects(pk=f.username).first()):
        raise login_invalid
    if not u.pw_chk(f.password):
        raise login_invalid

    token = generate_login_jwt(u, expires)
    response.set_cookie("Authorization", token, expires)
    return {"jwt": token}

class register_form(BaseModel):
    username: str
    password: str

@auth_route.post('/register')
async def register_auth(response: Response, f: OAuth2PasswordRequestForm = Depends()):
    """用户注册，令牌写在cookie里"""
    expires = 86400
    if User.objects(pk=f.username):
        raise HTTPException(400, 'user handle already exists')
    u = User(pk=f.username)
    u.pw_set(f.password)
    u.save()
    token = generate_login_jwt(u, expires)
    response.set_cookie("Authorization", token, expires)
    return {"jwt": token}


# from fapi.WebsocketSession import *
# from fastapi import WebSocket
# from fastapi import status
# @auth_route.websocket('/ws')
# async def ws_connectin(websocket: WebSocket, token: str = Query(''), typ: str=Query('plain')):
#     """
#     token: player对应的jwt口令，可以通过bot申请
#     typ: 欲创建的ws连接种类，仅提供json和plain两种
#     """
#     logger.debug(token)
#     p, msg = verify_player_jwt(token)
#     if not p:
#         await websocket.close(status.WS_1008_POLICY_VIOLATION)
#     if typ == 'json':
#         await SessionManager.hangon(await SessionManager.new(WebsocketSessionJson, websocket, p.pid))
#     elif typ == 'plain':
#         await SessionManager.hangon(await SessionManager.new(WebsocketSessionPlain, websocket, p.pid))
#     else:
#         await websocket.close(status.WS_1008_POLICY_VIOLATION)

    