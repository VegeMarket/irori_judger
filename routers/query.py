from config import static
# from collections import namedtuple

# P = namedtuple('P', ['page', 'perpage', 'tail'])

async def pagination(page: int=1, perpage:int=20) -> slice:
    perpage = min(static.perpage_limit, perpage)
    perpage = max(1, perpage)
    page = max(1, page)
    tail = page * perpage
    return slice(tail-perpage, tail)

# async def filter(p)