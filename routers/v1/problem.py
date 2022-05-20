import json
from routers.problem import list_filter
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form, status
from loguru import logger
from models.user import User
from models.problem import Problem
from routers.query import pagination
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from config import static
from jose import jwt


import hashlib
import datetime

import asyncio
problem_route = APIRouter(
    prefix="/problem",
    tags=["problem | 问题详细"],
)


@problem_route.get('')
async def get_problem_list(
    aggregation_P:dict = Depends(list_filter()),
    ):
    """查询问题表"""
    aggregation, P = aggregation_P
    res = Problem.objects.aggregate(aggregation).next()
    # logger.critical(res)
    total = res['totalCount'][0]['cnt']
    # problem_list = [i.get_visible_fields() for i in Problem.objects.exclude('desc')[P]]
    return {
        'data': res['paginated'],
        'perpage': len(res['paginated']),
        'total': total,
        'has_more': P.stop < total
    }


@problem_route.get('/{problem_id}')
async def get_problem(problem_id: str):
    p: Problem = Problem.objects(pk=problem_id).first()
    if not p:
        raise HTTPException(404, 'no such problem')
    return p.to_mongo()

# @problem_route.post('')
# async def create_problem():
#     raise HTTPException(402, '你给钱我就写')

# @problem_route.put('/{problem_id}')
# async def modify_problem(problem_id: str):
#     raise HTTPException(402, '你给钱我就写')

# @problem_route.delete('/{problem_id}')
# async def delete_problem(problem_id: str):
#     raise HTTPException(402, '你给钱我就写')