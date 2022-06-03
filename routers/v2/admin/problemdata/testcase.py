# generator_args
from typing import List
import zipfile
from .common import *

from pydantic import BaseModel, Field

class Case(BaseModel):
    infile: str = Field(None, alias='in')
    outfile: str = Field(None, alias='out')
    points: int = None
    generator_args: List[str] = []

class UpdatedCases(BaseModel):
    test_cases: List[Case]

def get_file_list():
    l = []
    base_path = problem_dir(g().problem_id)
    for i in os.listdir(base_path):
        fp = os.path.join(base_path, i)
        if os.path.isfile(fp):
            if i.endswith('.zip'):
                with zipfile.ZipFile(fp, 'r') as z:
                    for filename in z.namelist():
                        l.append(filename)
            else:
                l.append(i)
    return l

@problem_data_route.post('/testcase')
async def set_testcases(cases: UpdatedCases):
    """校验文件后替换本题的test_cases"""
    filelist = set(get_file_list())

    for c in cases.test_cases:
        if c.infile and c.infile not in filelist:
            raise HTTPException(404, 'not such file')
        if c.outfile and c.outfile not in filelist:
            raise HTTPException(404, 'not such file')
    
    y = readyml()
    y.update(cases.dict(by_alias=True, exclude_unset=True))
    saveyml(y)
    return y