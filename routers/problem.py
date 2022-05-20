from loguru import logger
from routers.query import pagination
from fastapi import Depends, HTTPException, status

# P = namedtuple('P', ['page', 'perpage', 'tail'])
def list_filter(public_only=True):
    async def list_filter_aggregation(
        P = Depends(pagination),
        order_by: str=None, 
        keyword: str=None,
        tags: str=None
    ):
        aggregation = []
        match = [{'is_public': True}] if public_only else []
        if keyword:
            match.append({
                'title': {
                    '$text': {
                        '$search': keyword,
                        '$caseSensitive': False,
                        '$diacriticSensitive': True
                    }
                }
            })
        if tags:
            match.append({
                '$or': [{'tags': {'name': t}} for t in tags.split(',')]
            })
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
            if key not in ('difficulty', '_id', 'title'):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, 'invalid sorting key')
            aggregation.append({
                '$sort':{
                    key: order
                }
            })
        
        projection = {
            'tags':1,
            'solved': 1,
            '_id': 1,
            'submitted': 1,
            'difficulty': 1,
            'title': 1
        }
        if not public_only: projection['is_public'] = 1
        aggregation.append({'$project': projection})


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
    return list_filter_aggregation
