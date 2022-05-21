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
from mongoengine.fields import *

from utils.motor import C, L

class SampleContest(Document, Asyncable):
    name = StringField(primary_key=True)
    li = ListField(StringField())

class SamplePart(Document, Asyncable):
    name = StringField(primary_key=True)
    c = LazyReferenceField(SampleContest)

class SampleSub(Document, Asyncable):
    part = LazyReferenceField(SamplePart)
    pro = StringField()
    s = StringField(default='0')

def poc():
    SampleContest.objects.delete()
    SamplePart.objects.delete()
    SampleSub.objects.delete()

    C1 = SampleContest(name='C1', li=['A', 'B']).save()
    P1 = SamplePart(name='P1', c=C1).save()
    P2 = SamplePart(name='P2', c=C1).save()
    P3 = SamplePart(name='P3', c=C1).save()

    P1S1 = SampleSub(part=P1, pro='A', s='0').save()
    P1S2 = SampleSub(part=P1, pro='A', s='1').save()
    P1S3 = SampleSub(part=P1, pro='A', s='1').save()
    P1S3 = SampleSub(part=P1, pro='A', s='1').save()
    P1S4 = SampleSub(part=P1, pro='B', s='0').save()
    P1S5 = SampleSub(part=P1, pro='B', s='1').save()

    P2S1 = SampleSub(part=P2, pro='A', s='1').save()
    P2S2 = SampleSub(part=P2, pro='B', s='1').save()

    P3S1 = SampleSub(part=P3, pro='A', s='0').save()

    res = SampleContest.objects.aggregate([
        {'$match': {'_id': C1.pk}},
        {'$project':{
            '_id': 1,
            # 'part':1
        }},
        {'$lookup': {
            'from':SamplePart._get_collection_name(),
            'localField': '_id',
            'foreignField': 'c',
            'as': 'part'
        }},
        {'$project':{
            'part._id':1
        }},
    ]).next()
    print(res) # 6.0.0rc5的MongoDB Community Server会崩 rc6没有复现，似乎修了

@pytest.mark.asyncio
async def test_asyncable():
    await SampleContest.armrf()
    await SamplePart.armrf()
    await SampleSub.armrf()
    SampleContest.objects.delete()
    SamplePart.objects.delete()
    SampleSub.objects.delete()

    C1 = SampleContest(name='C1', li=['A', 'B']).save()
    P1 = SamplePart(name='P1', c=C1).save()
    P2 = SamplePart(name='P2', c=C1).save()
    P3 = SamplePart(name='P3', c=C1).save()

    P1S1 = SampleSub(part=P1, pro='A', s='0').save()
    P1S2 = SampleSub(part=P1, pro='A', s='1').save()
    P1S3 = SampleSub(part=P1, pro='A', s='1').save()
    P1S3 = SampleSub(part=P1, pro='A', s='1').save()
    P1S4 = SampleSub(part=P1, pro='B', s='0').save()
    P1S5 = SampleSub(part=P1, pro='B', s='1').save()

    P2S1 = SampleSub(part=P2, pro='A', s='1').save()
    P2S2 = SampleSub(part=P2, pro='B', s='1').save()

    P3S1 = SampleSub(part=P3, pro='A', s='0').save()

    res = SamplePart.objects.aggregate([
        # {'$match': {'_id': C1.pk}},
        # {'$project':{
        #     '_id': 1,
        #     # 'part':1
        # }},
        # {'$lookup': {
        #     'from':SamplePart._get_collection_name(),
        #     'localField': '_id',
        #     'foreignField': 'c',
        #     'as': 'part'
        # }},
        {'$match': {'c': C1.pk}},
        {'$project':{
            '_id':1
        }},
        {'$lookup': {
            'from':SampleSub._get_collection_name(),
            'localField': '_id',
            'foreignField': 'part',
            'as': 'sub'
        }},
        {'$project':{
            '_id':0,
            'sub':1
        }},
        {'$unwind': {'path': '$sub'}},
        {'$facet':{
            'tried': [
                {'$group': {'_id': '$sub.pro', 'cnt': {'$count': {}}}}
            ],
            'solved': [
                {'$match': {'sub.s': '1'}},
                {'$group': {'_id': {'pro':'$sub.pro', 'part':'$sub.part'}}},
                {'$group': {'_id': '$_id.pro', 'pass': {'$count': {}}}},
            ]
        }}
        
    ]).next()
    print(res)
    assert res == {'tried': [{'_id': 'B', 'cnt': 3}, {'_id': 'A', 'cnt': 6}], 'solved': [{'_id': 'B', 'pass': 2}, {'_id': 'A', 'pass': 2}]}
    # print(res)
    # for p, i in enumerate(res):
        # print(p, i)
    # print(len(res))



if __name__ == '__main__':
    # poc()
    asyncio.run(test_asyncable())

