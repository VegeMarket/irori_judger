from loguru import logger
from routers.query import pagination
from fastapi import Depends, HTTPException, status

# P = namedtuple('P', ['page', 'perpage', 'tail'])

async def list_filter_aggregation(
    P = Depends(pagination),
    order_by: str=None, 
    problem: str=None,
    language: str=None,
    user: str=None,
    status: str=None,
    result: str=None
):
    aggregation = []

    match = []
    if problem: match.append({'problem': problem})
    if user: match.append({'user': user})
    if status: match.append({'status': status})
    if language: match.append({'language': language})
    if result: match.append({'result': result})

    if match:
        aggregation.append({
            '$match': {'$and': match}
        })
    if order_by:
        order, key = order_by[0], order_by[1:]
        if order == '+': # 升序
            order = 1
        elif order == '-':
            order = -1
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'invalid ordering')
        if key not in (
            'date', 
            '_id', 
            'time', 
            'memory', 
            'case_total', 
            'judged_date', 
            'rejudge_date',
            'points',
            'case_points',
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'invalid sorting key')
        aggregation.append({
            '$sort':{
                key: order
            }
        })
    
    aggregation.append({
        '$project':{
            'user':1,
            '_id': 1,
            'problem': 1,
            'language': 1,
            'date': 1,
            'time': 1,
            'memory': 1,
            'points':1,
            'status':1,
            'result':1,
            'current_testcase':1,
            'case_points':1,
            'case_total':1,
            'judged_date':1,
            'rejudge_date':1,
        }
    })

    paginated = []
    if P.start:
        paginated.append({'$skip': P.start})
    paginated.append({'$limit': P.stop})
    aggregation.append({
        '$facet':{
            'paginated': paginated,
            'totalCount':[{'$count': 'cnt'}]
        }
    })
    logger.debug(aggregation)
    return aggregation, P



# async def filter(p)