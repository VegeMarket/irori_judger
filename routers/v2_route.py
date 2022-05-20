import os
from fastapi import APIRouter, Depends, FastAPI
v2_router = APIRouter(
    prefix="/api/v2",
    tags=["Basic V2"],
    dependencies=[]
)
from utils.importer import route_importer, route_group_importer

dest_module = __name__.split('.')[:-1] + ['v2'] # router.v2
route_importer(dest_module, v2_router)
route_group_importer(dest_module, v2_router)

# for module in os.listdir(os.path.join(*os.path.split(os.path.dirname(__file__)) ,'v2')):
# for module in os.listdir(os.path.join(os.getcwd(), *my_module[:-1] ,'v2')):
#     if module == '__init__.py' or module[-3:] != '.py':
#         continue
#     module = module[:-3]
#     package = importlib.import_module(f"routers.v2.{module}")
#     router = getattr(package, f"{module}_route")
#     v2_router.include_router(router)

# from routers.v2.admin import admin_router
# v2_router.include_router(admin_router)
# from routers.v2.auth import auth_route
# from routers.v2.user import user_route
# from routers.v2.oss import oss_route
# from routers.v2.problem import problem_route
# from routers.v2.submission import submission_route
# from routers.v2.runtime import runtime_route


# v2_router.include_router(auth_route)
# v2_router.include_router(user_route)
# v2_router.include_router(oss_route)
# v2_router.include_router(problem_route)
# v2_router.include_router(submission_route)
# v2_router.include_router(runtime_route)

