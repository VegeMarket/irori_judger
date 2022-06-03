from fastapi import File, Query
from typing import List
from .common import *

def clear_checker() -> dict:
    y = readyml()
    if y is None:
        y = {}
    if c := y.get('checker'):
        if isinstance(c, dict) and c.get('name') == 'bridged':
            if args := c.get('args'):
                if isinstance(args['files'], list):
                    files = args['files']
                else:
                    files = [args['files']]
                for checker_file in files:
                    delete_file(checker_file)
        elif isinstance(c, str) and c.endswith('.py'):
            delete_file(c)
        y.pop('checker')
        saveyml(y)
    return y


@problem_data_route.post('/bridged_checker') # TODO: 全覆盖测试
async def set_bridged_checker(
    files: List[UploadFile] = File(...,
        title='checker源代码',
        description='如果有多个文件有include关系，则列表上传即可，第一个文件为入口文件'),
    lang: str = Query(...,
        title='源语言',
        description='checker的源码所用语言，与dmoj评测机语言简写一致，参见https://docs.dmoj.ca/#/judge/supported_languages'),
    type: str = Query('default',
        title='checker类型',
        description='''指定judger如何与checker交互，可选值有：
- default: 传给checker的参数顺序为input_file output_file judge_file，返回值0表示AC，1表示WA，其他表现为内部错误IE
- testlib: input_file output_file judge_file，返回值0=AC,1=WA,2=格式错误(PE),3=断言式失败,7且stderr输出格式为`points X`表示有`X`分的部分分
- coci: 类似testlib，但部分分stderr输出格式为`partial X/Y`，表示X/Y分
- peg: 兼容WCIPEG评测，鬼知道那是什么，不考虑支持'''
    ),
    time_limit: float = Query(None,
        gt=0,
        le=static.max_time_limit,
        title='checker运行时限'),
    memory_limit: int = Query(None,
        gt=0,
        le=static.max_memory_limit,
        title='checker运行内存限制'),
    compiler_time_limit: float = Query(None,
        gt=0,
        le=static.max_time_limit,
        title='checker编译时限'),
    feedback: bool = Query(True,
        title='checker stdout是否展示'),
    args_format_string: str = Query(None,
        title='自定义参数',
        description='随checker运行传入的命令行参数，从argv[1]开始'),
    flags: str = Query(None,
        title='checker编译选项',
        description='以空格隔开的编译选项，限制输入为大小写数字下划线等号减号空字符，不保证work（',
        regex=r'^[\sA-Za-z0-9_=\-]+$'),
    cached: bool = Query(True,
        title='编译型checker是否缓存其执行文件'),
    ):
    """上传一个自定义checker，详见参数说明，不会进行lang的校验"""
    if type not in ('default', 'testlib', 'coci', 'peg'):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'invalid checker type')
    problem_id = g().problem_id
    if len(files) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'checker source must provide')
    if len(files) > static.source_max_count:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'too many source files')
    source_list = []
    for file in files:
        validate_aux_filename(file.filename)
        validate_size(file)
        source_list.append(file.filename)

    y = clear_checker()
    for file in files:
        save_file(file)
        
    checker_config = y['checker'] = {'name': 'bridged'}
    args = checker_config['args'] = {}
    args['files'] = source_list
    args['lang'] = lang
    args['type'] = type
    if time_limit: args['time_limit'] = time_limit
    if memory_limit: args['memory_limit'] = memory_limit
    if compiler_time_limit: args['compiler_time_limit'] = compiler_time_limit
    if feedback: args['feedback'] = feedback
    if flags: args['flags'] = flags.split(' ')
    if cached: args['cached'] = cached
    if args_format_string: args['args_format_string'] = args_format_string

    saveyml(y)
    return y
    

@problem_data_route.delete('/checker')
async def delete_checker():
    """删除checker"""
    return clear_checker()
    
@problem_data_route.post('/custom_checker')
async def set_custom_checker(
    file: UploadFile = File(...,
        title='checker源文件',
        description='checker的py源码文件，扩展名必须是.py')):
    basename, ext = validate_aux_filename(file.filename)
    if ext != 'py':
        raise ill_ext
    problem_id = g().problem_id
    y = clear_checker()
    save_file(file)
    y['checker'] = file.filename
    saveyml(y)
    return y
    # with openW(problem_id, 'init.yml') as f:
    #     yaml.safe_dump(y, f)



@problem_data_route.post('/checker') # TODO: 全覆盖测试
async def set_builtin_checker(
    name: str = Query(title='内置checker类型，详见docstring'),
    precision: int = Query(None,
        ge=0,
        title='精度',
        description='floats族checker用，舍入到小数点后第几位'),
    error_mode: str = Query(None, 
        title='误差模式',
        description='floats族checker用，可选`default`(相对误差和绝对误差在范围内), `relative`(相对误差), `absolute`(绝对误差)'),
    pe_allowed: bool = Query(None,
        title='是否展示格式错误',
        description='identical用，如果是True，用户答案去除空格后与标准答案相等时会反馈PE'),
    feedback: bool = Query(None,
        title='按行反馈',
        description='linecount用，是否按行给出结果'),
    split_on: str = Query(None,
        title='无序依据',
        description='sorted族用，可选lines或whitespace，内容相等的情况下，lines行序不对判对，whitespace每行空格隔开的内容顺序不对也判对')
        ):
    """可选值：

    - standard: 默认checker，扔掉空行后逐行与judge输出比较
    - easy: 扔掉空格，检查每个字母的出现次数是否相等
    - floats: 特别为浮点误差准备的checker，可选`error_mode`和`precision`两个参数
    - floatsabs: 绝对误差浮点型checker
    - floatsrel: 相对误差浮点型checker
    - identical: 包括空格严格相等的checker, 可选`pe_allowed`参数
    - linecount: 按行比较的checker，可选`feedback`参数
    - sorted: 输出顺序无关checker，可选`split_on`参数，为lines时，行序不对但内容相等也判对
    - unordered: 同sorted，split_on设为whitespace
    """
    if name not in (
        'standard',
        'easy',
        'floats',
        'floatsabs',
        'floatsrel',
        'identical',
        'linecount',
        'sorted',
        'unordered',
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'invalid checker name')
    args = {}
    if precision and name in ('floats',
        'floatsabs',
        'floatsrel',):
        args['precision'] = precision
    if error_mode in ('default', 'relative', 'absolute') and name=='floats':
        args['error_mode'] = error_mode
    if pe_allowed and name == 'identical': args['pe_allowed'] = pe_allowed
    if feedback and name == 'linecount': args['feedback'] = feedback
    if split_on in ('whitespace', 'lines') and name == 'sorted': args['split_on'] = split_on
    y = clear_checker()
    if args:
        y['checker'] = {'name': name, 'args': args}
    else:
        y['checker'] = name
    saveyml(y)
    return y