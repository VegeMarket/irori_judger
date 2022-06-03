from typing import List
import zipfile

from fastapi import Form, Query, Response
from pydantic import BaseModel
from .common import *
from fastapi import File

class UploadResult(BaseModel):
    success: int = 0


@problem_data_route.post('/files')
async def upload_files(files: List[UploadFile] = File(...,
    description='选择上传的文件列表，仅校验文件名')):
    """考虑到用中间件限制了请求体大小，此处可能有的二进制文件会大于源码文件16kb的限制，故此处不额外设限
    
    对zip压缩包会有额外限制，里面的每个文件名必须也是英文数字下划线最多带一个."""
    for file in files:
        basename, ext = validate_aux_filename(file.filename)
        if ext == 'zip': # 额外校验压缩包里的每个文件，只有扩展名为.zip才会被认为是压缩包文件
            with zipfile.ZipFile(file.file) as z:
                for fn in z.namelist():
                    validate_aux_filename(fn)
            file.file.seek(0)
    res = UploadResult()
    for file in files:
        save_file(file)
        res.success += 1

    return res

class DeleteResult(BaseModel):
    success: int = 0
    not_found: List[str] = []

@problem_data_route.delete('/files')
async def delete_files(files: List[str] = Query(...)):
    logger.debug(files)
    for fn in files:
        validate_aux_filename(fn)
        if fn == 'init.yml':
            raise HTTPException(403, 'cannot remove init.yml by this api')
    res = DeleteResult()
    for fn in files:
        r = delete_file(fn)
        if r:
            res.success += 1
        else:
            res.not_found.append(fn)
    return res
    

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
    
    base_path = problem_dir(problem_id)
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
            logger.debug(fp)
            with zipfile.ZipFile(fp, 'r') as z:
                for info in z.infolist():
                    sonlist.append(
                        {info.filename: {
                            'size': info.file_size
                        }}
                    )
    return ret

