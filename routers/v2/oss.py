from io import BytesIO
from fastapi import APIRouter, HTTPException, Response
from loguru import logger
from models.oss import FileStorage

from pydantic import BaseModel
from jose import jwt
from urllib.parse import quote

import hashlib
import datetime
from config import secret
from utils.motor import afsdelete, afsread

import asyncio
oss_route = APIRouter(
    prefix="/oss",
    tags=["oss | 文件存储服务"],
)

E404 = HTTPException(404, 'No such resource')

async def _download_oss(fspk: str):
    fs: FileStorage = await FileStorage.atrychk(fspk)
    if not fs:
        raise E404
    if fs.expires and fs.expires < datetime.datetime.now():
        await fs.arelease()
        raise E404

    fn = fs.name
    content_disposition_filename = quote(fn)
    if content_disposition_filename != fn:
        content_disposition = "attachment; filename*=utf-8''{}".format(
            content_disposition_filename
        )
    else:
        content_disposition = f'attachment; filename="{fn}"'
    return Response((await afsread(fs.content)), media_type=fs.mime, headers={
        "content-disposition": content_disposition
    })


@oss_route.get('/{fspk}')
async def download_oss(fspk: str): return (await _download_oss(fspk))

@oss_route.post('/')
async def download_oss(fspk: str): return (await _download_oss(fspk))