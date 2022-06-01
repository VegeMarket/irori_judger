"""设计思路:

1. 不要另外建立题目数据数据模型，直接从给定文件夹中提取

2. 设计一种yml的解析和编辑方式，如不存在则放入一个模板

3. 在不存在文件夹时新建，先判断题目名称合法，为了防止ntfs大小写不敏感产生问题，限制题目名字为小写数字下划线

4. 运维应该自己准备一套轮子用来同步题目集，如fsync，onedrive


"""
import json
import re
import traceback
from typing import List

import yaml
from utils.jwt import should_granted, should_login
from routers.problem import list_filter
from fastapi import APIRouter, Cookie, Depends, HTTPException, Path, Query, Request, Response, File, UploadFile, Form, status
from loguru import logger
from models.user import AUTHORITY, User
from models.problem import Problem
from routers.query import pagination
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from config import static
from jose import jwt
from utils.ctx import g
from config import secret

import hashlib
import os

import datetime

import asyncio
problem_route = APIRouter(
    prefix="/problem",
    tags=["problem | 问题管理"],
    dependencies=[
        Depends(should_login),
        Depends(should_granted(AUTHORITY.ADMIN))]
)

@problem_route.get('')
async def get_problem_list(
    aggregation_P:dict = Depends(list_filter(False)),
    ):
    """查询问题表"""
    aggregation, P = aggregation_P
    res = (await Problem.aaggregate_list(aggregation))[0]
    # logger.critical(res)
    total = res['totalCount'][0]['cnt']
    return {
        'data': res['paginated'],
        'perpage': len(res['paginated']),
        'total': total,
        'has_more': P.stop < total
    }


@problem_route.get('/{problem_id}')
async def get_problem(problem_id: str):
    p: Problem = await Problem.atrychk(pk=problem_id)
    if not p:
        raise HTTPException(404, 'no such problem')
    return p.to_mongo()

@problem_route.post('/{problem_id}')
async def create_problem(problem_id: str):
    """新建一个问题，为其分配文件夹，写入init.yml文件"""
    if (await Problem.atrychk(problem_id)):
        raise HTTPException(400, 'problem already exists')
    await Problem(pk=problem_id).asave_report_error()
    dest_path = problem_dir(problem_id)
    if not os.path.exists(dest_path):
        os.mkdir(dest_path)
    
    if not os.path.exists(ymlfile:=os.path.join(dest_path, 'init.yml')):
        with open(ymlfile, 'w', newline='\n') as f:
            pass
            # f.write('\n')
    return Response(status_code=200)

import shutil

@problem_route.delete('/{problem_id}')
async def delete_problem(problem_id: str, remove_dir: bool=False):
    """删掉一个问题，如果指定remove_dir则会连同文件夹一起删除"""
    if not (p:=await Problem.atrychk(problem_id)):
        raise HTTPException(404, 'problem not exists')
    await p.adestroy()
    dest_path = problem_dir(problem_id)
    if remove_dir:
        shutil.rmtree(dest_path)
    return Response(status_code=200)

import zipfile


@problem_route.put('/{problem_id}')
async def modify_problem(problem_id: str):
    raise HTTPException(402, '你给钱我就写')

ill_pat = HTTPException(status.HTTP_403_FORBIDDEN, 'illegal pattern detected')

allow_filename = re.compile(r'^[0-9a-z_]+$')

def validate_pathstr(p: str):
    """在os文件操作前检查给定串是否满足白名单"""
    if not re.match(allow_filename, p): raise ill_pat

def validate_checker_filename(fn: str):
    basename, *ext = fn.split('.', 1)
    if ext:
        ext = ext[0]
        logger.debug(ext)
        validate_pathstr(ext)
    logger.debug(basename)
    validate_pathstr(basename)


async def validate_filename(problem_id: str = Path(
    title='问题主键，只能由小写字母、数字、下划线组成', 
    regex=r'^[0-9a-z_]+$')):
    # if not re.match(allow_filename, problem_id):
        # raise HTTPException(status.HTTP_403_FORBIDDEN, 'illegal problem_id detected')
    g().problem_id = problem_id

problem_data_route = APIRouter(
    prefix='/data/{problem_id}',
    tags=['problem data | 问题数据文件管理'],
    dependencies=[Depends(validate_filename)]
)

"""文件处理模块必须小心

严格限制文件大小，可以使用限额? <- 如果直接修改文件目录会变得难以维护，admin层可以不考虑

限额应该交给没有OS权限的管理用户使用(或者不用？)

考虑到admin可以直接管理文件夹，也许不考虑文件储存浪费比较好？

尽量避免将文件读入内存

注意初始的空文件init.yml会被load为None

init.yml指南：https://docs.dmoj.ca/#/problem_format/problem_format
    test_cases:
        必须含有test_cases键，指定一列测试用例或者两正则用于匹配输入和输出文件
        用列表的例子：
        test_cases:
            - {in: aplusb.1.in, out: aplusb.1.out, points: 5}
            - {in: aplusb.2.in, out: aplusb.2.out, points: 20}
            - {in: aplusb.3.in, out: aplusb.3.out, points: 75}
        用正则的例子：（未验证，不推荐）
        test_cases:
            input_format: ^(?=.*?\.in|in).*?(?:(?:^|\W)(?P<batch>\d+)[^\d\s]+)?(?P<case>\d+)[^\d\s]*$
            output_format: ^(?=.*?\.out|out).*?(?:(?:^|\W)(?P<batch>\d+)[^\d\s]+)?(?P<case>\d+)
            case_points: 1 # 调节每个batch或者case的分数
        points: 100 # 或者用points指定所有cases的总分
        关于test_case:
            包括通常版和子任务版，可以混搭：
            test_cases:
            - {points: 0, in: tle16p4.p0.in, out: tle16p4.p0.out}
            - {points: 10, in: tle16p4.p1.in, out: tle16p4.p1.out}
            - points: 10
            batched:
            - {in: tle16p4.0.in, out: tle16p4.0.out}
            - {in: tle16p4.1.in, out: tle16p4.1.out}
            - points: 10
            batched:
            - {in: tle16p4.2.in, out: tle16p4.2.out}
            - {in: tle16p4.3.in, out: tle16p4.3.out}
        当指定了archive后，测试点的路径都为压缩包内的路径
    checker:
        实现spj的工具
        可以使用dmoj内置的checker
        格式：
        checker:
            name: <name of checker>
            args: {}

    generator:
        可以在init.yml中指定generator键来指定一个cpp generator
        此题在运行时会执行这个cpp，
        将它运行结果的stdout作为生成的input
        stderr作为生成的output
        参考ds3的配置：
        generator: generator.cpp
        points: 5
        test_cases:
        - generator_args: [1]
        - generator_args: [2]
        - generator_args: [3]

os.stat文档：
st_mode: inode 保护模式
st_ino: inode 节点号。
st_dev: inode 驻留的设备。
st_nlink: inode 的链接数。
st_uid: 所有者的用户ID。
st_gid: 所有者的组ID。
st_size: 普通文件以字节为单位的大小；包含等待某些特殊文件的数据。
st_atime: 上次访问的时间。
st_mtime: 最后一次修改的时间。
st_ctime: 由操作系统报告的"ctime"。在某些系统上（如Unix）是最新的元数据更改的时间，在其它系统上（如Windows）是创建时间（详细信息参见平台的文档）。
"""

def problem_dir(problem_id, *args):
    """用前记得过滤路径参数"""
    return os.path.join(secret.problem_dir, problem_id, *args)

def file_size(file: UploadFile) -> int:
    """获取一个UploadFile的实际大小"""
    file.file.seek(0, 2)
    siz = file.file.tell()
    file.file.seek(0)
    return siz

@problem_data_route.get('/')
async def get_data_dir():
    """获取问题目录下的文件信息
    
    只展示非文件夹和压缩包内文件信息
    
    返回格式大致如下：{
        fname: {
            size: 114, 
            mtime: (时间戳)
        }, 
        zipname: {
            size: 514, 
            mtime: (修改时间戳), 
            son:[a: {size: 1919}]
        }
    }
    
    只有目录存在且含有init.yml会被显示
    
    问题id只能由小写字母、数字和下划线组合而成"""
    problem_id = g().problem_id
    validate_filename(problem_id)
    
    base_path = problem_dir(problem_id)
    if not os.path.exists(base_path) or not os.path.exists(os.path.join(base_path, 'init.yml')):
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'not such problem')
    ret = {}
    for i in os.listdir(base_path):
        fp = os.path.join(base_path, i)
        stat = os.stat(fp)
        ret[i] = {'size': stat.st_size, 'mtime': stat.st_mtime, 'type': 'file'}
        if os.path.isdir(fp):
            ret[i]['type'] = 'dir'
            # continue
        if i.endswith('.zip'):
            ret[i]['type'] = 'zip'
            sonlist = ret[i]['son'] = []
            with zipfile.ZipFile(fp, 'r') as z:
                for info in z.infolist():
                    sonlist.append(
                        {info.filename: {
                            'size': info.file_size
                        }}
                    )
    return ret

def clear_problem_dir(problem_id: str):
    base_path = problem_dir(problem_id)
    for i in os.listdir(base_path):
        if i != 'init.yml':
            fp = os.path.join(base_path, i)
            if os.path.isfile(fp):
                os.remove(fp)
            elif os.path.isdir(fp):
                shutil.rmtree(fp)
            else:
                raise OSError(f'irregular file: {fp}')

def clear_checker(problem_id: str) -> dict:
    path = problem_dir(problem_id, 'init.yml')
    with open(path, 'r', encoding='utf-8', newline='\n') as f:
        y = yaml.safe_load(f)
    if y is None:
        y = {}
    if c := y.get('checker'):
        if isinstance(c, dict) and c.get('name') == 'bridged':
            if isinstance(c['files'], list):
                files = c['files']
            else:
                files = [c['files']]
            for checker_file in files:
                validate_checker_filename(checker_file)
                try:
                    os.remove(problem_dir(problem_id, checker_file))
                except FileNotFoundError as exc: # 可能文件名无效，或者出于某种原因已经被删掉了
                    logger.critical(exc)
        y.pop('checker')
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            yaml.safe_dump(y, f)
    return y

safe_flags = re.compile(r'^[\sA-Za-z0-9_=\-]+$')
@problem_data_route.post('/bridged_checker') # TODO: 全覆盖测试
async def set_bridged_checker(
    files: List[UploadFile] = File(...,
        title='checker源代码',
        description='如果有多个文件有include关系，则列表上传即可'),
    lang: str = Query(...,
        title='源语言',
        description='checker的源码所用语言，与dmoj评测机语言简写一致，参见https://docs.dmoj.ca/#/judge/supported_languages'),
    type: str = Query(...,
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
    path = problem_dir(problem_id, 'init.yml')
    if len(files) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'checker source must provide')
    if len(files) > static.checker_source_max_count:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'too many source files')
    source_list = []
    for file in files:
        validate_checker_filename(file.filename)
        fz = file_size(file)
        if fz > static.source_code_limit:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'source length limit exceeded')
        source_list.append(file.filename)

    y = clear_checker(problem_id)
    for file in files:
        with open(problem_dir(problem_id, file.filename), 'wb') as f:
            f.write(file.file.read())
        
    # with open(path, 'r', encoding='utf-8', newline='\n') as f:
        # y = yaml.safe_load(f)
    ck = y['checker'] = {'name': 'bridged'}
    ck['files'] = source_list
    ck['lang'] = lang
    ck['type'] = type
    if time_limit: ck['time_limit'] = time_limit
    if memory_limit: ck['memory_limit'] = memory_limit
    if compiler_time_limit: ck['compiler_time_limit'] = compiler_time_limit
    if feedback: ck['feedback'] = feedback
    if flags: ck['flags'] = flags.split(' ')
    if cached: ck['cached'] = cached

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        yaml.safe_dump(y, f)
    return y
    

@problem_data_route.delete('/checker')
async def delete_checker():
    return clear_checker(g().problem_id)
    


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
    problem_id = g().problem_id
    path = problem_dir(problem_id, 'init.yml')

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
    y = clear_checker(problem_id)
    # with open(path, 'r', encoding='utf-8', newline='\n') as f:
        # y = yaml.safe_load(f)
    if args:
        y['checker'] = {'name': name, 'args': args}
    else:
        y['checker'] = name
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        yaml.safe_dump(y, f)
    return y

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
    problem_id = g().problem_id

    if len(new_yml) > static.problem_yml_limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
        f'yml file must not exceed {static.problem_yml_limit} bytes')
    try:
        y = yaml.safe_load(new_yml.content)
        with open(
            os.path.join(secret.problem_dir, problem_id, 'init.yml'), 'w', 
            encoding='utf-8', newline='\n') as f:
            yaml.safe_dump(y, f)
    except yaml.scanner.ScannerError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'not a valid yaml')
    except:
        logger.critical(traceback.format_exc())
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, 'unexpect yaml exception')

# @problem_data_route.put('/{problem_id}/data')
# async def modify_problem_data(problem_id: str):

# @problem_route.delete('/{problem_id}')
# async def delete_problem(problem_id: str):
#     raise HTTPException(402, '你给钱我就写')

problem_route.include_router(problem_data_route)
