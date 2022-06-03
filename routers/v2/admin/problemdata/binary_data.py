from .common import *

@problem_data_route.post('/binary_data')
async def set_binary_data():
    """指定binary_data选项，将文件作为二进制打开，建议配合identical的checker"""
    y = readyml()
    if y is None: y = {}
    if not y.get('binary_data'):
        y['binary_data'] = True
        saveyml(y)
    return y

@problem_data_route.delete('/binary_data')
async def unset_binary_data():
    """取消指定binary_data选项"""
    y = readyml()
    if y is None: y = {}
    if y.get('binary_data'):
        y.pop('binary_data')
    saveyml(y)
    return y
    