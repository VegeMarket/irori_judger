

from fastapi import APIRouter, Depends, FastAPI
v2_admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[]
)
from .problem import problem_route
v2_admin_router.include_router(problem_route)