

import os
from fastapi import APIRouter, Depends, FastAPI
from utils.importer import route_importer
admin_route = APIRouter(
    prefix="/admin",
    tags=["Admin | 狗管理专用"],
    dependencies=[]
)

route_importer(__name__.split('.'), admin_route)

# print(os.path.split(os.path.dirname(__file__)))
# print(os.getcwd())
# print(__name__)

# from .problem import problem_route
# admin_router.include_router(problem_route)