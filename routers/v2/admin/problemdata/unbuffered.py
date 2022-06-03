from .common import *

@problem_data_route.post('/unbuffered')
async def set_unbuffered():
    """指定unbuffered选项，让交互题选手程序不用手动flush，但可能稍微带来性能损失"""
    y = readyml()
    if y is None: y = {}
    if not y.get('unbuffered'):
        y['unbuffered'] = True
        saveyml(y)
    return y

@problem_data_route.delete('/unbuffered')
async def unset_unbuffered():
    """取消指定unbuffered选项"""
    y = readyml()
    if y is None: y = {}
    if y.get('unbuffered'):
        y.pop('unbuffered')
    saveyml(y)
    return y
