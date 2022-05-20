from fastapi import APIRouter, Depends, FastAPI
v1_router = APIRouter(
    prefix="/api/v1",
    tags=["Basic V1"],
    dependencies=[]
)

from routers.v1.auth import auth_route
from routers.v1.oss import oss_route
from routers.v1.problem import problem_route
from routers.v1.submission import submission_route
from routers.v1.runtime import runtime_route


v1_router.include_router(auth_route)
v1_router.include_router(oss_route)
v1_router.include_router(problem_route)
v1_router.include_router(submission_route)
v1_router.include_router(runtime_route)