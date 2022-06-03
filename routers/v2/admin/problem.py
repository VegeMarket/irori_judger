"""设计思路:

1. 不要另外建立题目数据数据模型，直接从给定文件夹中提取

2. 设计一种yml的解析和编辑方式，如不存在则放入一个模板

3. 在不存在文件夹时新建，先判断题目名称合法，为了防止ntfs大小写不敏感产生问题，限制题目名字为小写数字下划线

4. 运维应该自己准备一套轮子用来同步题目集，如fsync，onedrive


"""
import json
import re
import traceback
from typing import List, Tuple

import yaml
from utils.jwt import should_granted, should_login
from routers.problem import list_filter
from fastapi import APIRouter, Cookie, Depends, HTTPException, Path, Query, Request, Response, File, UploadFile, Form, status
from loguru import logger
from models.user import AUTHORITY, User
from models.problem import Problem
from routers.query import pagination
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from config import static
from jose import jwt
from utils.ctx import g
from config import secret

import hashlib
import os

import datetime

from .problemdata import problem_data_route, problem_dir

import asyncio
problem_route = APIRouter(
    prefix="/problem",
    tags=["problem | 问题管理"],
    dependencies=[
        Depends(should_login),
        Depends(should_granted(AUTHORITY.ADMIN))]
)

@problem_route.get('')
async def get_problem_list(
    aggregation_P:dict = Depends(list_filter(False)),
    ):
    """查询问题表"""
    aggregation, P = aggregation_P
    res = (await Problem.aaggregate_list(aggregation))[0]
    # logger.critical(res)
    total = res['totalCount'][0]['cnt']
    return {
        'data': res['paginated'],
        'perpage': len(res['paginated']),
        'total': total,
        'has_more': P.stop < total
    }


@problem_route.get('/{problem_id}')
async def get_problem(problem_id: str):
    p: Problem = await Problem.atrychk(pk=problem_id)
    if not p:
        raise HTTPException(404, 'no such problem')
    return p.to_mongo()

@problem_route.post('/{problem_id}')
async def create_problem(problem_id: str):
    """新建一个问题，为其分配文件夹，写入init.yml文件"""
    if (await Problem.atrychk(problem_id)):
        raise HTTPException(400, 'problem already exists')
    await Problem(pk=problem_id).asave_report_error()
    dest_path = problem_dir(problem_id)
    if not os.path.exists(dest_path):
        os.mkdir(dest_path)
    
    if not os.path.exists(ymlfile:=os.path.join(dest_path, 'init.yml')):
        with open(ymlfile, 'w', newline='\n') as f:
            yaml.safe_dump({}, f) # 放入一个空字典
    return Response(status_code=200)

import shutil

@problem_route.delete('/{problem_id}')
async def delete_problem(problem_id: str, remove_dir: bool=False):
    """删掉一个问题，如果指定remove_dir则会连同文件夹一起删除"""
    if not (p:=await Problem.atrychk(problem_id)):
        raise HTTPException(404, 'problem not exists')
    await p.adestroy()
    dest_path = problem_dir(problem_id)
    if remove_dir:
        shutil.rmtree(dest_path)
    return Response(status_code=200)

@problem_route.put('/{problem_id}')
async def modify_problem(problem_id: str):
    raise HTTPException(402, '你给钱我就写')


problem_route.include_router(problem_data_route)
