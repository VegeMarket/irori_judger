from loguru import logger
from utils.motor import afsdelete, afsput
from models.mixin.asyncable import Asyncable
from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
from models.mixin.chkable import Chkable
from io import BytesIO
import datetime
import magic
from config import static

class UploadLimitExceed(Exception): pass

class FileStorage(Document, Chkable, Asyncable):
    name = StringField()
    content = FileField()
    mime = StringField()
    expires = DateTimeField()
    date = DateTimeField()
    uploader = StringField() # 上传者用户handle，为了分离此处不做Ref

    def release(self):
        self.content.delete()
        self.delete()

    async def arelease(self):
        """释放自己及所存文件"""
        await afsdelete(self.content)
        await self.adestroy()

    def upload(fn: str, f: BytesIO):
        """上传者，过期时间不在这里处理"""
        typ = magic.from_buffer(f.read(1024), mime=True)
        f.seek(0)
        f_orm = FileStorage(name=fn, date=datetime.datetime.now(), mime=typ)
        f_orm.content.put(f)
        return f_orm.save()

    @classmethod
    async def aupload(cls, fn: str, f: BytesIO, uploader: str, 
        expires: datetime.datetime=None, space=None, limit: int=None, in_types:tuple=None):
        """f是个有read和seek和tell方法的玩意就行，猜解文件类型并上传，顺便更新space限额
        fn: 文件名
        uploader: 上传者用户handle
        expires: 如果指定，文件将于此时过期
        space: 空间限额，隔壁的Spacer对象
        limit: 限制文件大小多少bytes
        in_types: 限制文件的mime类型（用magic库猜解得到）
        """
        if expires and expires <= datetime.datetime.now():
            return
        if space or limit:
            f.seek(0, 2)
            siz = f.tell()
            logger.debug(f'siz: {siz}')
            if space:
                if space.used + siz > space.allow:
                    raise UploadLimitExceed(f'{space.used + siz - space.allow} bytes exceeded limits')
                space.used += siz
            if limit is not None and siz > limit:
                raise UploadLimitExceed(f'{siz - limit} bytes exceeded limits')
        f.seek(0)
        typ = magic.from_buffer(f.read(1024), mime=True)
        logger.info(f'guessed type: {typ}')
        if in_types and typ not in in_types:
            raise TypeError(f'{typ} is not in allowed types: {in_types}')
        f.seek(0)
        f_orm = FileStorage(name=fn, date=datetime.datetime.now(), mime=typ, 
            uploader=uploader)
        if expires: f_orm.expires = expires
        await afsput(f_orm.content, f, fn)
        saved = (await f_orm.asave())
        if space:
            space.file_list.append(saved.pk)
            await space.asave()

        return saved