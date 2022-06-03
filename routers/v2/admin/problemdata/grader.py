from fastapi import Response, File
from .common import *

def clear_grader() -> dict:
    y = readyml()
    if y is None: y = {}
    if gd := y.get('custom_judge'):
        delete_file(gd)
        y.pop('custom_judge')
        saveyml(y)
    return y

@problem_data_route.delete('/grader')
async def unset_grader():
    return clear_grader()

@problem_data_route.post('/grader') # TODO: 全覆盖测试
async def set_grader(
    file: UploadFile = File(...,
        title='源代码',
        description='重写grader的py源代码，要求扩展名必须是.py'),
    ):
    basename, ext = validate_aux_filename(file.filename)
    if ext != 'py':
        raise ill_ext
    validate_size(file)
    y = clear_grader()
    save_file(file)
    y['custom_judge'] = file.filename
    saveyml(y)
    return y