"""本文件为离线代码，测试motor用"""

# changed to parent path
# print(__name__)
if __name__ == '__main__':
    import os, sys
    cur = sys.path[0]
    parent = cur[:cur.rfind('\\')]
    os.chdir(parent)
    sys.path.append(parent)
    print(sys.path)

import asyncio
from io import BytesIO
# import pytest
import pytest_asyncio
import pytest
from config import secret
from motor.motor_asyncio import AsyncIOMotorClient
from models.problem import Problem
from models.judger import Judger
from utils.password import encrypt
db = AsyncIOMotorClient(secret.db_auth)[secret.db_name]

from models.mixin.asyncable import Asyncable
from mongoengine import Document
from mongoengine import StringField
from mongoengine.fields import FileField
from utils.motor import *

class TFS(Document, Asyncable):
    name = StringField(primary_key=True)
    f = FileField()

@pytest.mark.asyncio
async def test_asyncable():
    for i in (await L(TFS.objects)):
        i.f.delete()
    await TFS.armrf()
    t = TFS(name='A')
    b = BytesIO(b'AA')
    b.seek(0)
    t.f.put(b)
    t.save()

    t = TFS(name='B')
    await afsput(t.f, b'BB')
    await t.asave()

    t = TFS(name='C')
    b = BytesIO(b'CC')
    b.seek(0)
    await afsput(t.f, b)
    t.save()

    # t.f.put(b)


    t = await TFS.atrychk('A')
    assert t.f.read() == b'AA'
    assert (await afsread(t.f)) == b'AA'
    await afsdelete(t.f)

    t = await TFS.atrychk('B')
    assert t.f.read() == b'BB'
    assert (await afsread(t.f)) == b'BB'
    await afsdelete(t.f)

    t = await TFS.atrychk('C')
    assert t.f.read() == b'CC'
    assert (await afsread(t.f)) == b'CC'
    await afsdelete(t.f)




if __name__ == '__main__':
    asyncio.run(test_asyncable())

