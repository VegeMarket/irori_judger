import copy
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from loguru import logger
from models.user import User
from models.oss import FileStorage, UploadLimitExceed
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from jose import jwt

import hashlib
import datetime
from config import secret, static

from fastapi import status
from utils.jwt import generate_login_jwt, should_login
from utils.ctx import g
from mongoengine.errors import ValidationError

import asyncio
me_route = APIRouter(
    prefix="/me",
    tags=["me | 我的信息"],
    dependencies=[Depends(should_login)]
)

@me_route.get('/')
async def get_me():
    """获取指定用户的信息"""
    u = g().user.to_mongo()
    return {i:u[i] for i in (
        '_id',
        'avatar',
        'nick',
        'email',
        'desc',
        'last_access',
        'authority_level',
        'last_ip',
        'rating',
        'solved',
        'tried',
        'jwt_updated',
        'api_token',
    ) if i in u}

class UserInfoUpdated(BaseModel):
    desc: str = None
    email: str = None
    nick: str = None

@me_route.put('/')
async def update_me_info(updated: UserInfoUpdated):
    """用户更新自身信息"""
    u: User = g().user
    # old = copy.deepcopy(u)
    is_changed = False
    for k, v in updated.dict().items():
        if v:
            if getattr(u, k) != v:
                setattr(u, k, v)
                is_changed = True
    
    if not is_changed: raise HTTPException(400, 'no changes have been made')
    # if u == old: raise HTTPException(400, 'no changes have been made')
    # u == old 不对劲，不会比较两者字典
    await u.asave_report_error()
    return Response(status_code=200)

async def release_old_avatar():
    if g().user.avatar:
        provider, lnk = g().user.avatar.split(':', 1)
        if provider == 'oss':
            fs: FileStorage = await FileStorage.atrychk(lnk)
            if not fs:
                logger.warning(f'FS not found: {lnk}') # 可能已经被删掉但是没更新user
                return
                # raise Exception(f'FS not found: {lnk}')
            await fs.arelease()


@me_route.put('/avatar')
async def update_avatar(token: str):
    if ':' not in token:
        raise HTTPException(400, 'illegal avatar format')
    provider, lnk = token.split(':', 1)
    if provider not in ('qq', 'github',): # TODO: [Security] 外部url会不会被xss
        raise HTTPException(400, 'illegal avatar provider')
    await release_old_avatar()
    g().user.avatar = token
    await g().user.asave_report_error()
    return Response(status_code=200)

@me_route.post('/avatar')
async def upload_avatar(f: UploadFile = File(...)):
    try:
        avatar_fs = await FileStorage.aupload(
            f.filename,
            f.file,
            g().user.pk,
            limit=static.avatar_limit,
            in_types=('image/png','image/jpeg', 'image/gif', 'image/x-ms-bmp', 'image/webp')
        )
    except UploadLimitExceed as e:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(e))
    except TypeError as e:
        raise HTTPException(400, str(e))
    await release_old_avatar()
    g().user.avatar = f'oss:{avatar_fs.pk}'
    await g().user.asave()
    return Response(status_code=200)
