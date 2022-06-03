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

from typing import Tuple
import os
import re
import shutil
from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile, status
from loguru import logger
import yaml
from config import secret, static
from utils.ctx import g

ill_pat = HTTPException(status.HTTP_403_FORBIDDEN, 'illegal pattern detected')
ill_ext = HTTPException(status.HTTP_400_BAD_REQUEST, 'invalid file extension')

pat_filename = re.compile(r'^[0-9a-z_]+$')
pat_flags = re.compile(r'^[\sA-Za-z0-9_=\-]+$')


def problem_dir(problem_id, *args):
    """用前记得过滤路径参数"""
    return os.path.join(secret.problem_dir, problem_id, *args)

def file_size(file: UploadFile) -> int:
    """获取一个UploadFile的实际大小"""
    file.file.seek(0, 2)
    siz = file.file.tell()
    file.file.seek(0)
    return siz
    
# def clear_problem_dir(problem_id: str):
#     base_path = problem_dir(problem_id)
#     for i in os.listdir(base_path):
#         if i != 'init.yml':
#             fp = os.path.join(base_path, i)
#             if os.path.isfile(fp):
#                 os.remove(fp)
#             elif os.path.isdir(fp):
#                 shutil.rmtree(fp)
#             else:
#                 raise OSError(f'irregular file: {fp}')
                
async def validate_problem_id(problem_id: str = Path(
    description='问题主键，只能由小写字母、数字、下划线组成', 
    regex=r'^[0-9a-z_]+$')):
    if not os.path.exists(problem_dir(problem_id)) or not os.path.exists(problem_dir(problem_id, 'init.yml')):
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'not such problem') 
    g().problem_id = problem_id



def validate_pathstr(p: str):
    """在os文件操作前检查给定串是否满足白名单"""
    if not re.match(pat_filename, p): raise ill_pat


def validate_size(file: UploadFile, limit=static.source_code_limit):
    """校验一个UploadFile的大小是否合乎源码长度限制"""
    if file_size(file) > limit:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'source length limit exceeded')

def validate_aux_filename(fn: str) -> Tuple[str, str]:
    """校验一个文件名是否满足白名单规则"""
    basename, *ext = fn.split('.', 1)
    if ext:
        ext = ext[0]
        logger.debug(ext)
        validate_pathstr(ext)
    else:
        ext = ''
    logger.debug(basename)
    validate_pathstr(basename)
    return basename, ext

def openR(*args):
    return open(problem_dir(*args), 'r', encoding='utf-8', newline='\n')
def openRB(*args):
    return open(problem_dir(*args), 'rb')
def openW(*args):
    return open(problem_dir(*args), 'w', encoding='utf-8', newline='\n')
def openWB(*args):
    return open(problem_dir(*args), 'wb')

def save_file(file: UploadFile):
    with openWB(g().problem_id, file.filename) as f:
        logger.debug(f'write: {f.write(file.file.read())}')

def delete_file(filename: str):
    validate_aux_filename(filename)
    try:
        os.remove(problem_dir(g().problem_id, filename))
    except FileNotFoundError as exc: # 可能文件名无效，或者出于某种原因已经被删掉了
        logger.critical(exc)
        return False
    return True

def readyml():
    with openR(g().problem_id, 'init.yml') as f:
        return yaml.safe_load(f)

def saveyml(y):
    with openW(g().problem_id, 'init.yml') as f:
        yaml.safe_dump(y, f)



problem_data_route = APIRouter(
    prefix='/data/{problem_id}',
    tags=['problem data | 问题数据文件管理'],
    dependencies=[Depends(validate_problem_id)]
)
