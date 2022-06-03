from .common import *
from pydantic import BaseModel
import traceback

@problem_data_route.get('/yml')
async def get_problem_yml():
    problem_id = g().problem_id

    path = os.path.join(secret.problem_dir, problem_id, 'init.yml')
    with open(path, 'r', encoding='utf-8', newline='\n') as f:
        return f.read()


class NewYml(BaseModel):
    content: str

@problem_data_route.put('/yml')
async def set_problem_yml(new_yml: NewYml):
    """直接擦写init.yml文件，不会处理checker、interactor、grader的文件，只会进行yml的语法校验"""
    problem_id = g().problem_id

    if len(new_yml.content) > static.problem_yml_limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
        f'yml file must not exceed {static.problem_yml_limit} bytes')
    try:
        y = yaml.safe_load(new_yml.content)
        with open(
            os.path.join(secret.problem_dir, problem_id, 'init.yml'), 'w', 
            encoding='utf-8', newline='\n') as f:
            yaml.safe_dump(y, f)
        return y
    except yaml.scanner.ScannerError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'not a valid yaml')
    except:
        logger.critical(traceback.format_exc())
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, 'unexpect yaml exception')
