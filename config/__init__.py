"""读取全局设置文件的模块

计划同时支持env文件和yml文件，后者优先
"""

import shutil
import yaml
from utils.jsondict import JsonDict
import uvicorn
import os
from loguru import logger

class static: # 可公开的首选项配置
    judger_monitor_config = {
        'host':'0.0.0.0',
        'port':19998
    }
    site_server_config = uvicorn.Config(
        'svr:app',
        '0.0.0.0',
        19999,
        # ssl_certfile='ssl/A.crt', # 本地调试用自签证书
        # ssl_keyfile='ssl/A.key',
        # reload=True, # 这个选项不用uvicorn启动没用
        # workers=4, # 在有有效的迁移方案前先保持单进程运行，大概也够用
        # 要不以后整个服务读写分离吧，写api单线程，与judger交互
    )
    perpage_limit = 50 # 分页元素个数最大限制
    
    source_code_limit = 256 * 1024 # 源码长度限制
    max_time_limit = 10 # 10s任何程序运行时间上限
    max_memory_limit = 1024 * 1024 # 1GB任何程序运行内存上限

    oss_host = 'http://127.0.0.1'
    authenticate_judger = False # 是否开启评测机口令认证

    content_size_limit = 1024 * 1024 * 1024 # 每个请求体（包括上传文件）的大小限制，这里是1G

    submission_case_max_feedback = 65536 # 提交返信长度限制
    judge_handler_update_rate_time = 0.5
    judge_handler_update_rate_limit = 5

    file_storage_default_limit_user = 1024 * 1024 * 1024 # 用户空间附件限额，这里默认给1GB
    file_storage_default_limit_contest = 128 * 1024 * 1024 # 比赛空间附件限额，这里默认给128MB
    file_storage_default_limit_problem = 128 * 1024 * 1024 # 题目空间附件限额，这里默认给128MB

    avatar_limit = 261120 # 头像限制大小，这里限制为GridFS一个块大小，255kb
    gridfs_chunk_size = 261120 # GridFS中一个分块的大小，这里取默认的255kb

    problem_yml_limit = 16 * 1024 # 每个问题的init.yml限制大小
    source_max_count = 10 # checker和interactor的源码文件个数限制

if not os.path.exists('secret.yml'):
    logger.warning('secret.yml not found, copy secret.template.yml instead.')
    shutil.copyfile('secret.template.yml', 'secret.yml')
with open('secret.yml', 'r', newline='\n', encoding='utf-8') as f:
    secret = JsonDict(yaml.safe_load(f)) # 包含敏感数据的配置