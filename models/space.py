from email.policy import default
from mongoengine.queryset import *
from models.mixin.asyncable import Asyncable
from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
from io import BytesIO
import datetime
import magic
from config import static
from models.user import User
from models.contest import Contest
from models.problem import Problem
from models.oss import FileStorage

class Spacer:
    used = LongField(default=0) # 已用空间
    file_list = ListField(ReferenceField(FileStorage))


class SpaceUser(Document, Asyncable, Spacer):
    """用户附件空间限额，由于遍历统计效率不高所以手动维护一个"""
    user = ReferenceField(User, primary_key=True, reverse_delete_rule=CASCADE) # 用户索引
    allow = LongField(default=static.file_storage_default_limit_user) # 授权空间

class SpaceProblem(Document, Asyncable, Spacer):
    """题目附件空间限额，由于遍历统计效率不高所以手动维护一个"""
    problem = ReferenceField(Problem, primary_key=True, reverse_delete_rule=CASCADE) # 用户索引
    allow = LongField(default=static.file_storage_default_limit_problem) # 授权空间

class SpaceContest(Document, Asyncable, Spacer):
    """题目附件空间限额，由于遍历统计效率不高所以手动维护一个"""
    contest = ReferenceField(Contest, primary_key=True, reverse_delete_rule=CASCADE) # 用户索引
    allow = LongField(default=static.file_storage_default_limit_contest) # 授权空间

