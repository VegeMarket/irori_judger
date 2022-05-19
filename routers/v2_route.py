from fastapi import APIRouter, Depends, FastAPI
v2_router = APIRouter(
    prefix="/api/v2",
    tags=["All"],
    dependencies=[]
)

from routers.v2.auth import auth_route
from routers.v2.oss import oss_route
from routers.v2.problem import problem_route
from routers.v2.submission import submission_route
from routers.v2.runtime import runtime_route


v2_router.include_router(auth_route)
v2_router.include_router(oss_route)
v2_router.include_router(problem_route)
v2_router.include_router(submission_route)
v2_router.include_router(runtime_route)

