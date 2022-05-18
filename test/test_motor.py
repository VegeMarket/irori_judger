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

from utils.motor import C, L

class DocumentStringPK(Document, Asyncable):
    name = StringField(primary_key=True)
    default_val = StringField(default='value')
    null_val = StringField(null=True)
    something_else = StringField()

class DocumentObjectIDPK(Document, Asyncable):
    default_val = StringField(default='value')
    null_val = StringField(null=True)
    something_else = StringField()

@pytest.mark.asyncio
async def test_asyncable():
    await DocumentStringPK.armrf()
    await DocumentObjectIDPK.armrf()

    t = DocumentStringPK(name='123', something_else='sth')
    await t.asave()
    assert t.name == '123' and t.something_else == 'sth' and t.default_val == 'value' and t.null_val == None
    tt = await DocumentStringPK.achk('123')
    tt, t = t, tt
    assert t.name == '123' and t.something_else == 'sth' and t.default_val == 'value' and t.null_val == None
    assert tt == t


    t2 = await DocumentObjectIDPK().asave()
    t3 = await DocumentObjectIDPK().asave()
    assert t2 != t3
    print(t2.to_mongo(), t3.to_mongo())

    assert DocumentObjectIDPK.objects.count() == 2
    assert DocumentStringPK.objects.count() == 1

    t = await DocumentStringPK.atrychk('1234')
    assert t is None

    t = await DocumentStringPK.atrychk('123')
    assert t.name == '123' and t.something_else == 'sth' and t.default_val == 'value' and t.null_val == None
    t.default_val = 'changed'
    await t.asave()

    t = await DocumentStringPK.achk('123', projection={'_id':True, 'null_val':True}) # 虽然还会填上default但是不会改了
    t.null_val = 'a3'
    print(t.to_mongo())
    await t.asave()

    t = await DocumentStringPK.atrychk('123')
    assert t.name == '123' and t.something_else == 'sth' and t.default_val == 'changed' and t.null_val == 'a3'

    t = await DocumentStringPK.amock('123')
    assert t.name == '123' and t.something_else == 'sth' and t.default_val == 'changed' and t.null_val == 'a3'
    t = await DocumentStringPK.amock('1234')
    print(t.to_mongo())
    assert t.name == '1234' and t.something_else is None and t.default_val == 'value' and t.null_val is None

    assert DocumentStringPK.objects.count() == 1

    t = await DocumentStringPK.apop('123')
    assert DocumentStringPK.objects.count() == 0
    assert t.name == '123' and t.something_else == 'sth' and t.default_val == 'changed' and t.null_val == 'a3'

    t = await DocumentStringPK.achk('123')
    assert DocumentStringPK.objects.count() == 1
    assert t.name == '123' and t.something_else is None and t.default_val == 'value' and t.null_val is None
    t = await DocumentStringPK.aunchk('123')
    assert DocumentStringPK.objects.count() == 0
    t = await DocumentStringPK.afind_one({})
    assert t is None
    t = await DocumentStringPK.aensure('123') # 旧版本不要这个功能
    assert bool(t) == True
    assert t.raw_result.get('upserted')
    t = await DocumentStringPK.aensure('123') # 旧版本不要这个功能
    assert t.raw_result.get('upserted') is None

    assert DocumentStringPK.objects.count() == 1
    t = await DocumentStringPK.atrychk('123')
    assert t.name == '123' and t.something_else is None and t.default_val == 'value' and t.null_val is None

    t = await DocumentStringPK.aupd(pk='123', default_val='v')
    if t:
        print(t)
    else:
        assert False

    t = await DocumentStringPK.aupd(pk='1234', default_val='v')
    # t = DocumentStringPK.objects(pk='1234').update(default_val='v')
    if t:
        assert False
    else:
        print(t)
    
    t = await DocumentStringPK.atrychk('123')
    assert t.name == '123' and t.something_else is None and t.default_val == 'v' and t.null_val is None

    t = await DocumentStringPK.aupdate_one({'_id': '123'}, {'$set': dict(default_val='w')})
    assert t
    t = await DocumentStringPK.atrychk('123')
    assert t.name == '123' and t.something_else is None and t.default_val == 'w' and t.null_val is None
    assert (await DocumentStringPK.acount({})) == 1

    await DocumentStringPK.achk('1')
    await DocumentStringPK.achk('2')
    await DocumentStringPK.achk('3')
    await DocumentStringPK.achk('4')
    await DocumentStringPK.achk('5')

    t = await L(DocumentStringPK.objects.filter(pk__lt='8212345').only('pk', 'default_val')[0:10])
    assert(len(t)==6)
    t = await L(DocumentStringPK.objects.filter(pk__lt='2212345').only('pk', 'default_val'))
    assert(len(t)==3)
    t = await L(DocumentStringPK.objects.filter(pk__lt='9').only('pk', 'default_val')[0:10].order_by('default_val').as_pymongo())
    assert t == [{'_id': '1', 'default_val': 'value'}, {'_id': '2', 'default_val': 'value'}, {'_id': '3', 'default_val': 'value'}, {'_id': '4', 'default_val': 'value'}, {'_id': '5', 'default_val': 'value'}, {'_id': '123', 'default_val': 'w'}]

    print(t)


    # t = TesterDocumentStringPK
    # await t2.asave()

    # t = await TesterDocumentStringPK.atrychk('123')
    # t.something_else = '7fdasc'
    # t.null_val = 'fdykachkihe'
    # t.default_val = 'feacvrfgrea'
    # await t.asave()

    
    # t = TesterDocumentStringPK.get_default()

    # t = TesterDocumentStringPK.objects.exclude('default_val').first()
    # t.null_val='a1'
    # t.save()

    # t = await TesterDocumentStringPK.achk('123', projection={'_id':True, 'null_val':True}) # 虽然还会填上default但是不会改了
    # t.null_val = 'a3'
    # await t.asave()
    # print(t.to_mongo())

    await DocumentStringPK.armrf()
    await DocumentObjectIDPK.armrf()

if __name__ == '__main__':
    asyncio.run(test_asyncable())

