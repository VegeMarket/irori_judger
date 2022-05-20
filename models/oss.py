from utils.motor import afsput
from models.mixin.asyncable import Asyncable
from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
from models.mixin.chkable import Chkable
from io import BytesIO
import datetime
import magic
from config import static

class UploadLimitExceed(Exception):
    pass

class FileStorage(Document, Chkable, Asyncable):
    name = StringField()
    content = FileField()
    mime = StringField()
    expires = DateTimeField()
    date = DateTimeField()
    uploader = StringField() # 上传者用户handle，为了分离此处不做Ref
    def destroy(self):
        self.content.delete()
        self.delete()
    def upload(fn: str, f: BytesIO):
        """上传者，过期时间不在这里处理"""
        typ = magic.from_buffer(f.read(1024), mime=True)
        f.seek(0)
        f_orm = FileStorage(name=fn, date=datetime.datetime.now(), mime=typ)
        f_orm.content.put(f)
        return f_orm.save()

    @classmethod
    async def aupload(cls, fn: str, f: BytesIO, uploader, expires=None, space=None):
        """f是个有read和seek和tell方法的玩意就行，猜解文件类型并上传，顺便更新space限额"""
        if expires and expires <= datetime.datetime.now():
            return
        if space:
            f.seek(0, 2)
            siz = f.tell()
            if space.used + siz > space.allow:
                raise UploadLimitExceed(f'{space.used + siz - space.allow} bytes exceeded limits')
            space.used += siz
        f.seek(0)
        typ = magic.from_buffer(f.read(1024), mime=True)
        f.seek(0)
        f_orm = FileStorage(name=fn, date=datetime.datetime.now(), mime=typ, 
            uploader=uploader)
        if expires: f_orm.expires = expires
        await afsput(f_orm.content, f)
        saved = (await f_orm.asave())
        if space:
            space.file_list.append(saved.pk)
            await space.asave()

        return saved