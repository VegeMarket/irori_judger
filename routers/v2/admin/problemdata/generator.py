from .common import *
from typing import List
from fastapi import File, Query

def clear_generator() -> dict:
    y = readyml()
    if y is None: y = {}
    if it := y.get('generator'):
        if isinstance(it, dict):
            files = it['source']
        else:
            files = it
        if not isinstance(files, list):
            files = [files]
        for generator_file in files:
            delete_file(generator_file)
        y.pop('generator')
        saveyml(y)
    return y

@problem_data_route.delete('/generator')
async def unset_generator():
    """移除generator"""
    return clear_generator()

@problem_data_route.post('/generator') # TODO: 全覆盖测试
async def set_generator(
    files: List[UploadFile] = File(...,
        title='源代码',
        description='如果有多个文件有include关系，则列表上传即可，其中第一个是入口文件，其余的是辅助文件'),
    language: str = Query(...,
        title='源语言',
        description='generator的源码所用语言，与dmoj评测机语言简写一致，参见https://docs.dmoj.ca/#/judge/supported_languages'),
    time_limit: float = Query(None,
        gt=0,
        le=static.max_time_limit,
        title='运行时限',
        description='generator运行时限',
        ),
    memory_limit: int = Query(None,
        gt=0,
        le=static.max_memory_limit,
        title='运行内存限制'),
    compiler_time_limit: float = Query(None,
        gt=0,
        le=static.max_time_limit,
        title='编译时限'),
    flags: str = Query(None,
        title='编译选项',
        description='以空格隔开的编译选项，限制输入为大小写数字下划线等号减号空字符，不保证work（',
        regex=r'^[\sA-Za-z0-9_=\-]+$'),

    ):
    """上传一个自定义generator，详见参数说明，不会进行lang的校验，

    generator会在选手程序之前运行，generator输出的stdout会作为标准输入，stderr会作为标准输出
    
    当一个testcase同时拥有in和out两个键指定了标准输入输出文件时，generator不会被运行"""
    if len(files) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'generator source must provide')
    if len(files) > static.source_max_count:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'too many source files')
    source_list = []
    for file in files:
        validate_aux_filename(file.filename)
        validate_size(file)
        source_list.append(file.filename)

    y = clear_generator()
    for file in files:
        save_file(file)
        
    args = y['generator'] = {}
    args['source'] = source_list
    args['language'] = language
    if time_limit: args['time_limit'] = time_limit
    if memory_limit: args['memory_limit'] = memory_limit
    if compiler_time_limit: args['compiler_time_limit'] = compiler_time_limit
    if flags: args['flags'] = flags.split(' ')

    saveyml(y)
    return y