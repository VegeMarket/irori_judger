from fastapi import status
from fastapi import WebSocket
import json
from utils.jwt import should_login
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from models.user import User
from models.submission import Submission
from models.submission import Problem
from routers.submission import list_filter_aggregation


from utils.broadcast import broadcaster

from pydantic import BaseModel
from config import static
from jose import jwt
from utils.ctx import g
from judge.judge_list import judge_list
import hashlib
import datetime

import asyncio
submission_route = APIRouter(
    prefix="/submission",
    tags=["submission | 代码提交"],
    dependencies=[Depends(should_login)]
)


@submission_route.get('/')
async def get_submission_list(aggregation_P = Depends(list_filter_aggregation)):
    """查询提交记录（分页"""
    aggregation, P = aggregation_P
    res = (await Problem.aaggregate_list(aggregation))[0]
    total = res['totalCount'][0]['cnt']


    return {
        'data': res['paginated'],
        'perpage': len(res['paginated']),
        'total': total,
        'has_more': P.stop < total
    }


class Submit(BaseModel):
    source: str
    problem_id: str
    lang: str


@submission_route.post('/')
async def create_submission(submit: Submit):
    s = await Submission(
        user=g().user,
        problem=submit.problem_id,
        language=submit.lang,
        source=submit.source,
        date=datetime.datetime.now()
    ).asave_report_error()
    asyncio.create_task(judge_list.judge(
        s.pk,
        submit.problem_id,
        submit.lang,
        submit.source,
        None,
        3
    ))

    return {'submission_id': s.pk}

from judge.judge_list import judge_list
@submission_route.websocket('/{submission_id}')
async def submission_async_detail(websocket: WebSocket, submission_id: str):
    """实时评测状态信息转发"""
    if submission_id in judge_list.submission_map:
        async with broadcaster.subscribe('sub_'+submission_id) as subscriber:
            async for event in subscriber:
                if event.message.get('type') == 'done-submission':
                    await websocket.close(status.WS_1000_NORMAL_CLOSURE)
                    return
                await websocket.send_text(event.message)
    await websocket.close(status.WS_1000_NORMAL_CLOSURE)


# from fapi.WebsocketSession import *
# @auth_route.websocket('/ws')


@submission_route.get('/{submission_id}')
async def get_submission(submission_id: int):
    p: Submission = await Submission.atrychk(submission_id)
    if not p:
        raise HTTPException(404, 'no such submission')
    return p.to_mongo()


# @submission_route.put('/{submission_id}')
# async def modify_submission(submission_id: str):
#     return 'to be done'


# @submission_route.delete('/{submission_id}')
# async def delete_submission(submission_id: str):
#     return 'to be done'
