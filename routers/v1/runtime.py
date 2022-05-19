import json
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, File, UploadFile, Form
from models.runtime import Runtime

runtime_route = APIRouter(
    prefix="/runtime",
    tags=["runtime | 运行环境"],
)

@runtime_route.get('/')
async def get_runtime_list():
    runtime_list = Runtime.objects.as_pymongo()
    return {
        'data': runtime_list,
    }

