from config import secret
import motor.motor_asyncio

client = motor.motor_asyncio.AsyncIOMotorClient(secret.db_auth)
db = client[secret.db_name]

# MongoEngine的queryset在切片的时候不会查库，会返回一个设置了偏移的queryset
# 只有在查询具体对象的时候会查库
from mongoengine.queryset import QuerySet

def C(self: QuerySet):
    """抄的mongoengine
    
    对self._collection下毒提取queryset的cursor并改成Motor的形状

    Return a PyMongo cursor object corresponding to this queryset."""
    # motor_collection = motor.motor_asyncio.AsyncIOMotorCollection(db, self._collection.name)
    motor_collection = db[self._collection.name]

    # If _cursor_obj already exists, return it immediately.
    # if self._cursor_obj is not None:
        # return self._cursor_obj

    # Create a new PyMongo cursor.
    # XXX In PyMongo 3+, we define the read preference on a collection
    # level, not a cursor level. Thus, we need to get a cloned collection
    # object using `with_options` first.
    if self._read_preference is not None or self._read_concern is not None:
        self._cursor_obj = motor_collection.with_options(
            read_preference=self._read_preference, read_concern=self._read_concern
        ).find(self._query, **self._cursor_args)
    else:
        self._cursor_obj = motor_collection.find(self._query, **self._cursor_args)

    # Apply "where" clauses to cursor
    if self._where_clause:
        where_clause = self._sub_js_fields(self._where_clause)
        self._cursor_obj.where(where_clause)

    # Apply ordering to the cursor.
    # XXX self._ordering can be equal to:
    # * None if we didn't explicitly call order_by on this queryset.
    # * A list of PyMongo-style sorting tuples.
    # * An empty list if we explicitly called order_by() without any
    #   arguments. This indicates that we want to clear the default
    #   ordering.
    if self._ordering:
        # explicit ordering
        self._cursor_obj.sort(self._ordering)
    elif self._ordering is None and self._document._meta["ordering"]:
        # default ordering
        order = self._get_order_by(self._document._meta["ordering"])
        self._cursor_obj.sort(order)

    if self._limit is not None:
        self._cursor_obj.limit(self._limit)

    if self._skip is not None:
        self._cursor_obj.skip(self._skip)

    if self._hint != -1:
        self._cursor_obj.hint(self._hint)

    if self._collation is not None:
        self._cursor_obj.collation(self._collation)

    if self._batch_size is not None:
        self._cursor_obj.batch_size(self._batch_size)

    if self._comment is not None:
        self._cursor_obj.comment(self._comment)

    return self._cursor_obj

async def L(queryset: QuerySet):
    """根据给定的queryset直接获取结果表"""
    cursor = C(queryset.clone())
    if queryset._scalar:
        return [queryset._get_scalar(
            queryset._document._from_son(
                i,
                _auto_dereference=False,
            )
        ) for i in (await cursor.to_list(length=None))]

    if queryset._as_pymongo:
        return (await cursor.to_list(length=None))

    return [queryset._document._from_son(
        i,
        _auto_dereference=False,
    ) for i in (await cursor.to_list(length=None))]