import enum
from models.mixin.asyncable import Asyncable
from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
import hashlib
from utils.password import encrypt
from mongoengine.queryset import *

AUTHORITY_LEVEL = (
    (0, 'admin'),
    (1, 'operator'),
    (2, 'officer'),
    (3, 'default'),
    (4, 'guest'),
)
"""
鉴权目标：
    OJ钦定传人、开发人员掌握admin
    运维打杂退役老嘢掌握operator
    受信的老队员掌握officer
    一般通过用户掌握default
"""
class AUTHORITY:
    ADMIN = 0
    OPERATOR = 1
    OFFICER = 2
    DEFAULT = 3
    GUEST = 4

class User(Document, Asyncable):
    """用户主体"""
    # 认证！（字正腔圆）
    handle = StringField(primary_key=True, regex=r'^[0-9a-zA-Z_]+$')
    password = StringField()
    password_reset_key = StringField() # 重设密码的令牌，忘记密码用
    jwt_updated = DateTimeField() # 密码更新时间，令之前的失效
    
    email = EmailField()
    email_verify_key = StringField() # 验证邮箱的令牌
    
    authority_level = IntField(default=AUTHORITY.DEFAULT, choices=AUTHORITY_LEVEL) # 不使用传统的RBAC，权限只分：狗管理、OJ运维人员、一般出题人（类似cf教练）、一般用户、游客
    
    # 社交
    avatar = StringField(max_length=256)     # 头像url
    nick = StringField(max_length=128)    # 昵称
    desc = StringField(max_length=128*1024)    # 这个人很懒.jpg

    last_access = DateTimeField()   # 上次登录
    last_ip = StringField()         # 上次ip

    rating = IntField(default=1500) # 留作后用
    solved = ListField(LazyReferenceField('Problem'))
    tried = ListField(LazyReferenceField('Problem'))

    api_token = StringField() # 注意维护唯一性

    def pw_chk(self, password: str) -> bool:
        return self.password == encrypt(password)

    def pw_set(self, password: str) -> "User":
        self.password = encrypt(password)
        return self

    @classmethod
    async def after_submission(cls, submission):
        """更新solved和tried状态，或者未来有什么状态也要一起更新"""
        pid = submission.problem.pk
        if submission.result not in ('IE', 'CE'):
            if submission.result == 'AC':
                return (await cls.aupdate_one(
                    {'_id': pid},
                    {
                        '$addToSet': {'solved':pid},
                        '$pull': {'tried': pid}
                    }
                ))
            else:
                return (await cls.aupdate_one(
                    {'_id': pid, 'solved': {'$ne': pid}},
                    {'$addToSet': {'tried': pid}}
                ))
        return False