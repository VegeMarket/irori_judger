from fastapi import File, Query
from typing import List
from .common import *

def clear_interactor() -> dict:
    y = readyml()
    if y is None: y = {}
    if it := y.get('interactive'):
        files = it['files']
        if not isinstance(files, list):
            files = [files]
        for interactor_file in files:
            delete_file(interactor_file)
        y.pop('interactive')
        saveyml(y)
    return y

@problem_data_route.delete('/interactive')
async def unset_interactor():
    """移除interactor"""
    return clear_interactor()

@problem_data_route.post('/interactive') # TODO: 全覆盖测试
async def set_interactor(
    files: List[UploadFile] = File(...,
        title='源代码',
        description='如果有多个文件有include关系，则列表上传即可，但只有第一个文件作为入口文件'),
    lang: str = Query(...,
        title='源语言',
        description='interactor的源码所用语言，与dmoj评测机语言简写一致，参见https://docs.dmoj.ca/#/judge/supported_languages'),
    type: str = Query('default',
        title='类型',
        description='''指定judger如何与interactor交互，可选值有：
- default: **注意与checker不同**，传给interactor的参数顺序为input_file judge_file，返回值0表示AC，1表示WA，其他表现为内部错误IE
- testlib: input_file output_file judge_file，其中`output_file`总是指向`/dev/null`，返回值0=AC,1=WA,2=格式错误(PE),3=断言式失败,7且stderr输出格式为`points X`表示有`X`分的部分分
- coci: 入参顺序input_file judge_file，大致类似testlib，但部分分stderr输出格式为`partial X/Y`，表示X/Y分
- peg: 鬼知道那是什么，官方文档也劝你别在这里用'''
    ),
    preprocessing_time: float = Query(None,
        gt=0,
        le=static.max_time_limit,
        title='预处理时限',
        description='因为加入interactor而为这题额外增加的运行时限，总时限=preprocessing_time+提交问题运行时限',
        ),
    memory_limit: int = Query(None,
        gt=0,
        le=static.max_memory_limit,
        title='运行内存限制'),
    compiler_time_limit: float = Query(None,
        gt=0,
        le=static.max_time_limit,
        title='编译时限'),
    args_format_string: str = Query(None,
        title='自定义参数',
        description='随interactor运行传入的命令行参数，从argv[1]开始'),
    flags: str = Query(None,
        title='编译选项',
        description='以空格隔开的编译选项，限制输入为大小写数字下划线等号减号空字符，不保证work（',
        regex=r'^[\sA-Za-z0-9_=\-]+$'),

    ):
    """上传一个自定义interactor，详见参数说明，不会进行lang的校验，
    interactor的stdin会收到来自选手程序的stdout，反之亦然"""
    if type not in ('default', 'testlib', 'coci'):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'invalid interactor type')
    if len(files) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'interactor source must provide')
    if len(files) > static.source_max_count:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'too many source files')
    source_list = []
    for file in files:
        validate_aux_filename(file.filename)
        validate_size(file)
        source_list.append(file.filename)

    y = clear_interactor()
    for file in files:
        save_file(file)
        
    args = y['interactive'] = {}
    args['files'] = source_list
    args['lang'] = lang
    args['type'] = type
    if preprocessing_time: args['preprocessing_time'] = preprocessing_time
    if memory_limit: args['memory_limit'] = memory_limit
    if compiler_time_limit: args['compiler_time_limit'] = compiler_time_limit
    if flags: args['flags'] = flags.split(' ')
    if args_format_string: args['args_format_string'] = args_format_string

    saveyml(y)
    return y